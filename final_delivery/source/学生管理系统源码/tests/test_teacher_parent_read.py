from teacher_scope_support import scoped_teacher


def test_parent_contacts_read_only_and_scoped(scoped_teacher):
    auth, ids = scoped_teacher
    path = f"/teacher/students/{ids.own}/parents"
    response = auth.client.get(path)
    assert response.status_code == 200
    assert "本班虚构家长" in response.text and "000-4011" in response.text
    assert "外班虚构家长" not in response.text and "000-4012" not in response.text
    assert auth.client.get(f"/teacher/students/{ids.course_only}/parents?class_id={ids.own_class}").status_code == 403
    assert auth.client.post(path, data={"csrf_token": auth.token("/profile"), "phone": "000-4999"}).status_code == 405
