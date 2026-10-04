from sqlalchemy.exc import IntegrityError
from app import create_app
from app.extensions import db
from app.models import University, Faculty, Department, Level, Course

app = create_app("production")

AAUA = "Adekunle Ajasin University, Akungba-Akoko"

STRUCTURE = {
    "Faculty of Agriculture": ["Agricultural Economics", "Agricultural Extension and Rural Development",
        "Animal Science", "Agronomy", "Fisheries and Aquaculture", "Forestry and Wildlife Management"],
    "Faculty of Arts": ["English Studies", "History and International Studies", "Linguistics and Languages",
        "Performing Arts", "Philosophy", "Religion and African Culture"],
    "Faculty of Education": ["Adult Education", "Arts Education", "Educational Management",
        "Guidance and Counselling", "Early Childhood Education", "Science Education", "Human Kinetics",
        "Health Education", "Industrial Technology and Vocational Education"],
    "Faculty of Science": ["Biochemistry", "Chemical Sciences (Chemistry)", "Computer Science",
        "Animal and Environmental Biology", "Earth Sciences", "Mathematical Sciences", "Microbiology",
        "Physics and Electronics", "Plant Science and Biotechnology"],
    "Faculty of Law": ["Commercial and Industrial Law", "Jurisprudence and International Law",
        "Private and Property Law", "Public Law"],
    "Faculty of Social Sciences": ["Economics", "Political Science", "Psychology", "Sociology",
        "Criminology and Security Studies", "Geography and Planning Sciences", "Mass Communication"],
    "Faculty of Administration & Management Sciences": ["Accounting", "Banking and Finance",
        "Business Administration", "Public Administration"],
    "Faculty of Environmental Design & Management": ["Architecture", "Estate Management",
        "Geography and Planning Sciences", "Surveying and Geoinformatics"],
    "Faculty of Computing": ["Computer Science", "Cyber Security", "Data Science",
        "Information and Communication Technology (ICT)", "Information Systems", "Software Engineering"],
    "Faculty of Allied Health Sciences": ["Nursing Science", "Medical Laboratory Science", "Public Health"],
}

TITLES = {
    100: ["Introduction to Computer Science", "Introduction to Programming", "Mathematics I",
          "Mathematics II", "General Physics I", "General Physics II", "General Chemistry",
          "Communication in English I", "Communication in English II", "Logic and Critical Thinking",
          "Introduction to Information Technology", "Computer Hardware Basics", "Basic Statistics",
          "Introduction to Algorithms", "Digital Literacy", "Introduction to Web Design",
          "Citizenship and Nigerian Peoples", "Entrepreneurship Studies I", "Technical Writing",
          "Introduction to Problem Solving"],
    200: ["Data Structures", "Object-Oriented Programming", "Discrete Mathematics", "Linear Algebra",
          "Computer Architecture", "Operating Systems I", "Database Design", "Numerical Methods",
          "Probability and Statistics", "Web Development", "Digital Logic Design",
          "Systems Analysis and Design", "Introduction to Networking", "Software Engineering I",
          "Python Programming", "Java Programming", "Assembly Language",
          "Human-Computer Interaction", "Entrepreneurship Studies II", "Computer Ethics"],
    300: ["Database Systems", "Operating Systems II", "Computer Networks", "Software Engineering II",
          "Algorithms and Complexity", "Artificial Intelligence", "Compiler Construction",
          "Mobile App Development", "Computer Graphics", "Information Security",
          "Web Application Development", "Formal Languages and Automata", "Data Mining",
          "Cloud Computing", "Embedded Systems", "Machine Learning Basics", "Distributed Systems",
          "Research Methods", "Industrial Training", "Internet Programming"],
    400: ["Final Year Project I", "Final Year Project II", "Advanced Machine Learning",
          "Deep Learning", "Cybersecurity", "Big Data Analytics", "Natural Language Processing",
          "Computer Vision", "Advanced Database Systems", "Software Project Management",
          "Parallel Computing", "Blockchain Technology", "Internet of Things", "Cryptography",
          "Data Science", "Advanced Networks", "Professional Practice", "Seminar",
          "Mobile Computing", "Systems Programming"],
}

with app.app_context():
    host = db.engine.url.host or ""
    print("Database host:", host)
    if "render.com" not in host:
        raise SystemExit("Not connected to the live database. Stopping.")

    # 1. Remove placeholder data from the other universities
    try:
        other_ids = [u.id for u in University.query.filter(University.name != AAUA).all()]
        fac_ids = [f.id for f in Faculty.query.filter(
            Faculty.university_id.in_(other_ids), Faculty.name == "Faculty of Science").all()]
        dept_ids = [d.id for d in Department.query.filter(Department.faculty_id.in_(fac_ids)).all()]
        Course.query.filter(Course.department_id.in_(dept_ids)).delete(synchronize_session=False)
        Department.query.filter(Department.id.in_(dept_ids)).delete(synchronize_session=False)
        Faculty.query.filter(Faculty.id.in_(fac_ids)).delete(synchronize_session=False)
        db.session.commit()
        print("Placeholders removed.")
    except IntegrityError:
        db.session.rollback()
        raise SystemExit("Some placeholder data is already in use. Nothing was deleted.")

    # 2. AAUA
    uni = University.query.filter_by(name=AAUA).first()
    if not uni:
        uni = University(name=AAUA)
        db.session.add(uni)
        db.session.flush()

    levels = {}
    for n in TITLES:
        lv = Level.query.filter_by(level_number=n).first()
        if not lv:
            lv = Level(level_number=n)
            db.session.add(lv)
            db.session.flush()
        levels[n] = lv

    # 3. Faculties and departments
    cs_depts = []
    for fname, depts in STRUCTURE.items():
        fac = Faculty.query.filter_by(university_id=uni.id, name=fname).first()
        if not fac:
            fac = Faculty(university_id=uni.id, name=fname)
            db.session.add(fac)
            db.session.flush()
        for dname in depts:
            d = Department.query.filter_by(faculty_id=fac.id, name=dname).first()
            if not d:
                d = Department(faculty_id=fac.id, name=dname)
                db.session.add(d)
                db.session.flush()
            if dname == "Computer Science":
                cs_depts.append(d)

    # 4. Sample courses under both Computer Science departments
    added = 0
    for d in cs_depts:
        have = {c.course_code for c in Course.query.filter_by(department_id=d.id).all()}
        for n, titles in TITLES.items():
            for i, title in enumerate(titles, start=1):
                code = f"CSC{n // 100}{i:02d}"
                if code not in have:
                    db.session.add(Course(course_code=code, course_title=title,
                                          department_id=d.id, level_id=levels[n].id))
                    added += 1

    db.session.commit()
    print("Done. Faculties:", Faculty.query.count(),
          "Departments:", Department.query.count(), "Courses added:", added)