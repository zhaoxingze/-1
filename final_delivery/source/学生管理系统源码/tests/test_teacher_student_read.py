from teacher_scope_support import scoped_teacher


def test_homeroom_list_and_profile_only_include_own_class(scoped_teacher):
    auth, ids = scoped_teacher
    classes = auth.client.get("/teacher/classes")
    assert classes.status_code == 200
    assert "负责班级" in classes.text and "外部班级" not in classes.text
    listing = auth.client.get(f"/teacher/classes/{ids.own_class}/students")
    assert listing.status_code == 200
    assert "AUTH-S1" in listing.text and "AUTH-S2" not in listing.text
    assert auth.client.get(f"/teacher/classes/{ids.other_class}/students").status_code == 403
    detail = auth.client.get(f"/teacher/students/{ids.own}")
    assert detail.status_code == 200 and "000-4001" in detail.text
    assert auth.client.get(f"/teacher/students/{ids.course_only}").status_code == 403


def test_course_only_roster_deduplicates_and_withholds_private_fields(scoped_teacher):
    auth, ids = scoped_teacher
    courses = auth.client.get("/teacher/courses")
    assert courses.status_code == 200
    assert "本教师课程" in courses.text and "其他教师课程" not in courses.text
    roster = auth.client.get(f"/teacher/courses/{ids.own_course}/students?student_id={ids.unrelated}")
    assert roster.status_code == 200
    assert roster.text.count("AUTH-S2") == 1 and "虚构学生2" in roster.text
    for private in ("SCOPE-OTHER", "000-4002", "虚构任课学生私有地址", "98.75", "外班虚构家长"):
        assert private not in roster.text
    assert auth.client.get(f"/teacher/courses/{ids.other_course}/students").status_code == 403
    assert auth.client.get(f"/admin/students/{ids.course_only}").status_code == 403
    assert auth.client.get(f"/students/{ids.course_only}/profile").status_code == 403


def test_course_pagination_preserves_search_and_scope(scoped_teacher):
    import re
    from html import unescape

    auth, ids = scoped_teacher
    page = auth.client.get(f"/teacher/courses/{ids.own_course}/students?per_page=1&q=AUTH")
    assert page.status_code == 200 and "AUTH-S1" in page.text and "AUTH-S2" not in page.text
    next_link = re.search(r'href="([^"]+)">下一页</a>', page.text)
    assert next_link and "q=AUTH" in unescape(next_link.group(1))
    second = auth.client.get(unescape(next_link.group(1)))
    assert second.status_code == 200 and "AUTH-S2" in second.text and "SCOPE-OTHER" not in second.text
