import pytest


def test_student_can_read_own_minimal_profile_but_not_others(auth):
    auth.login("auth_student")
    response = auth.client.get(f"/students/{auth.student_ids[0]}/profile")
    assert response.status_code == 200 and "AUTH-S1" in response.text
    assert "AUTH-S2" not in response.text
    for student_id in (auth.student_ids[1], 99999):
        assert auth.client.get(f"/students/{student_id}/profile?user_id={auth.ids['other_student']}").status_code == 403


def test_teacher_has_no_implicit_all_student_access(auth):
    auth.login("auth_teacher")
    assert auth.client.get(f"/students/{auth.student_ids[0]}/profile").status_code == 403


def test_admin_profile_read_is_authorized_and_missing_object_is_404(auth):
    auth.login()
    assert auth.client.get(f"/students/{auth.student_ids[0]}/profile").status_code == 200
    assert auth.client.get("/students/99999/profile").status_code == 404


@pytest.mark.parametrize("username,action,allowed", [("auth_student","read_grades",True), ("auth_student","read_attendance",True), ("auth_student","read_courses",True), ("auth_student","write_grades",False), ("auth_student","read_rewards",False), ("auth_admin","unknown",False), ("auth_teacher","read_profile",False)])
def test_object_permission_service_defaults_deny(auth, username, action, allowed):
    from app.extensions import db
    from app.models import User
    from app.services.permission_service import can_access_student_resource
    with auth.app.app_context():
        user = db.session.get(User,auth.ids[username])
        assert can_access_student_resource(user,auth.student_ids[0],action=action) is allowed
        assert can_access_student_resource(user,True,action=action) is False
