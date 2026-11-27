"""Initial thirteen domain tables

Revision ID: fab16ef0dd6f
Revises: 
Create Date: 2026-11-16 18:59:18.375355

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fab16ef0dd6f'
down_revision = None
branch_labels = None
depends_on = None


SQLITE_TRIGGERS = {'audit_logs_no_update': '\n'
                         'CREATE TRIGGER IF NOT EXISTS audit_logs_no_update\n'
                         'BEFORE UPDATE ON audit_logs\n'
                         'BEGIN\n'
                         "    SELECT RAISE(ABORT, 'audit logs are append-only');\n"
                         'END\n',
 'audit_logs_no_delete': '\n'
                         'CREATE TRIGGER IF NOT EXISTS audit_logs_no_delete\n'
                         'BEFORE DELETE ON audit_logs\n'
                         'BEGIN\n'
                         "    SELECT RAISE(ABORT, 'audit logs are append-only');\n"
                         'END\n',
 'parent_contacts_parent_insert': '\n'
                                  'CREATE TRIGGER IF NOT EXISTS parent_contacts_parent_insert\n'
                                  'BEFORE INSERT ON parent_contact_logs\n'
                                  'WHEN NEW.parent_id IS NOT NULL AND NOT EXISTS (\n'
                                  '    SELECT 1 FROM parents WHERE parent_id = NEW.parent_id AND '
                                  'student_id = NEW.student_id\n'
                                  ')\n'
                                  'BEGIN\n'
                                  "    SELECT RAISE(ABORT, 'contact parent must belong to the same "
                                  "student');\n"
                                  'END\n',
 'parent_contacts_parent_update': '\n'
                                  'CREATE TRIGGER IF NOT EXISTS parent_contacts_parent_update\n'
                                  'BEFORE UPDATE OF parent_id, student_id ON parent_contact_logs\n'
                                  'WHEN NEW.parent_id IS NOT NULL AND NOT EXISTS (\n'
                                  '    SELECT 1 FROM parents WHERE parent_id = NEW.parent_id AND '
                                  'student_id = NEW.student_id\n'
                                  ')\n'
                                  'BEGIN\n'
                                  "    SELECT RAISE(ABORT, 'contact parent must belong to the same "
                                  "student');\n"
                                  'END\n',
 'notifications_parent_insert': '\n'
                                'CREATE TRIGGER IF NOT EXISTS notifications_parent_insert\n'
                                'BEFORE INSERT ON notification_logs\n'
                                'WHEN NEW.parent_id IS NOT NULL AND NOT EXISTS (\n'
                                '    SELECT 1 FROM parents WHERE parent_id = NEW.parent_id AND '
                                'student_id = NEW.student_id\n'
                                ')\n'
                                'BEGIN\n'
                                "    SELECT RAISE(ABORT, 'notification parent must belong to the "
                                "same student');\n"
                                'END\n',
 'notifications_parent_update': '\n'
                                'CREATE TRIGGER IF NOT EXISTS notifications_parent_update\n'
                                'BEFORE UPDATE OF parent_id, student_id ON notification_logs\n'
                                'WHEN NEW.parent_id IS NOT NULL AND NOT EXISTS (\n'
                                '    SELECT 1 FROM parents WHERE parent_id = NEW.parent_id AND '
                                'student_id = NEW.student_id\n'
                                ')\n'
                                'BEGIN\n'
                                "    SELECT RAISE(ABORT, 'notification parent must belong to the "
                                "same student');\n"
                                'END\n',
 'parents_preserve_history_owner': '\n'
                                   'CREATE TRIGGER IF NOT EXISTS parents_preserve_history_owner\n'
                                   'BEFORE UPDATE OF student_id ON parents\n'
                                   'WHEN EXISTS (\n'
                                   '    SELECT 1 FROM parent_contact_logs\n'
                                   '    WHERE parent_id = OLD.parent_id AND student_id != '
                                   'NEW.student_id\n'
                                   ') OR EXISTS (\n'
                                   '    SELECT 1 FROM notification_logs\n'
                                   '    WHERE parent_id = OLD.parent_id AND student_id != '
                                   'NEW.student_id\n'
                                   ')\n'
                                   'BEGIN\n'
                                   "    SELECT RAISE(ABORT, 'parent reassignment conflicts with "
                                   "existing history');\n"
                                   'END\n'}


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('roles',
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=30), nullable=False),
    sa.Column('description', sa.String(length=200), nullable=True),
    sa.CheckConstraint("name IN ('admin','teacher','student')", name='ck_roles_name'),
    sa.PrimaryKeyConstraint('role_id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('teachers',
    sa.Column('teacher_id', sa.Integer(), nullable=False),
    sa.Column('teacher_no', sa.String(length=30), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('phone', sa.String(length=30), nullable=True),
    sa.Column('email', sa.String(length=100), nullable=True),
    sa.PrimaryKeyConstraint('teacher_id'),
    sa.UniqueConstraint('teacher_no')
    )
    op.create_table('courses',
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('course_code', sa.String(length=30), nullable=False),
    sa.Column('course_name', sa.String(length=100), nullable=False),
    sa.Column('credit', sa.Float(), nullable=False),
    sa.Column('teacher_id', sa.Integer(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['teacher_id'], ['teachers.teacher_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('course_id'),
    sa.UniqueConstraint('course_code')
    )
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_courses_teacher_id'), ['teacher_id'], unique=False)

    op.create_table('school_classes',
    sa.Column('class_id', sa.Integer(), nullable=False),
    sa.Column('class_name', sa.String(length=50), nullable=False),
    sa.Column('grade', sa.String(length=30), nullable=False),
    sa.Column('homeroom_teacher_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['homeroom_teacher_id'], ['teachers.teacher_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('class_id')
    )
    with op.batch_alter_table('school_classes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_school_classes_homeroom_teacher_id'), ['homeroom_teacher_id'], unique=False)

    op.create_table('students',
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('student_no', sa.String(length=30), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('gender', sa.String(length=10), nullable=False),
    sa.Column('birth_date', sa.Date(), nullable=True),
    sa.Column('phone', sa.String(length=30), nullable=True),
    sa.Column('address', sa.String(length=255), nullable=True),
    sa.Column('class_id', sa.Integer(), nullable=True),
    sa.Column('enrollment_date', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='enrolled', nullable=False),
    sa.Column('is_archived', sa.Boolean(create_constraint=True, name='ck_students_is_archived'), server_default=sa.text('0'), nullable=False),
    sa.CheckConstraint("status IN ('enrolled','suspended','graduated','withdrawn')", name='ck_students_status'),
    sa.ForeignKeyConstraint(['class_id'], ['school_classes.class_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('student_id'),
    sa.UniqueConstraint('student_no')
    )
    with op.batch_alter_table('students', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_students_class_id'), ['class_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_students_status'), ['status'], unique=False)

    op.create_table('enrollments',
    sa.Column('enrollment_id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('semester', sa.String(length=30), nullable=False),
    sa.Column('usual_score', sa.Float(), nullable=True),
    sa.Column('exam_score', sa.Float(), nullable=True),
    sa.Column('total_score', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint('exam_score IS NULL OR (exam_score >= 0 AND exam_score <= 100)', name='ck_enrollments_exam_score'),
    sa.CheckConstraint('total_score IS NULL OR (total_score >= 0 AND total_score <= 100)', name='ck_enrollments_total_score'),
    sa.CheckConstraint('usual_score IS NULL OR (usual_score >= 0 AND usual_score <= 100)', name='ck_enrollments_usual_score'),
    sa.ForeignKeyConstraint(['course_id'], ['courses.course_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('enrollment_id'),
    sa.UniqueConstraint('student_id', 'course_id', 'semester', name='uq_enrollments_student_course_semester')
    )
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_enrollments_course_id'), ['course_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_enrollments_semester'), ['semester'], unique=False)
        batch_op.create_index(batch_op.f('ix_enrollments_student_id'), ['student_id'], unique=False)

    op.create_table('parents',
    sa.Column('parent_id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('relationship', sa.String(length=20), nullable=False),
    sa.Column('phone', sa.String(length=30), nullable=False),
    sa.Column('email', sa.String(length=100), nullable=True),
    sa.Column('is_primary', sa.Boolean(create_constraint=True, name='ck_parents_is_primary'), server_default=sa.text('0'), nullable=False),
    sa.CheckConstraint("relationship IN ('father','mother','guardian','other')", name='ck_parents_relationship'),
    sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('parent_id')
    )
    with op.batch_alter_table('parents', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_parents_student_id'), ['student_id'], unique=False)
        batch_op.create_index('uq_parents_primary_per_student', ['student_id'], unique=True, sqlite_where=sa.text('is_primary = 1'))

    op.create_table('users',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=True),
    sa.Column('teacher_id', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(create_constraint=True, name='ck_users_is_active'), server_default=sa.text('1'), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['role_id'], ['roles.role_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['teacher_id'], ['teachers.teacher_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('user_id'),
    sa.UniqueConstraint('student_id'),
    sa.UniqueConstraint('teacher_id'),
    sa.UniqueConstraint('username')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_role_id'), ['role_id'], unique=False)

    op.create_table('attendance_records',
    sa.Column('attendance_id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('attendance_date', sa.Date(), nullable=False),
    sa.Column('period', sa.String(length=30), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('note', sa.String(length=255), nullable=True),
    sa.Column('recorded_by', sa.Integer(), nullable=False),
    sa.CheckConstraint("status IN ('present','late','absent','leave')", name='ck_attendance_status'),
    sa.ForeignKeyConstraint(['recorded_by'], ['users.user_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('attendance_id'),
    sa.UniqueConstraint('student_id', 'attendance_date', 'period', name='uq_attendance_student_date_period')
    )
    with op.batch_alter_table('attendance_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_attendance_records_attendance_date'), ['attendance_date'], unique=False)
        batch_op.create_index(batch_op.f('ix_attendance_records_recorded_by'), ['recorded_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_attendance_records_student_id'), ['student_id'], unique=False)

    op.create_table('audit_logs',
    sa.Column('audit_id', sa.Integer(), nullable=False),
    sa.Column('actor_user_id', sa.Integer(), nullable=True),
    sa.Column('entity_type', sa.String(length=80), nullable=False),
    sa.Column('entity_id', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=30), nullable=False),
    sa.Column('before_data', sa.JSON(none_as_null=True), nullable=True),
    sa.Column('after_data', sa.JSON(none_as_null=True), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('request_id', sa.String(length=100), nullable=True),
    sa.CheckConstraint("action IN ('create','update','archive','restore','status_change','delete')", name='ck_audit_logs_action'),
    sa.ForeignKeyConstraint(['actor_user_id'], ['users.user_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('audit_id')
    )
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_logs_actor_user_id'), ['actor_user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_entity_id'), ['entity_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_entity_type'), ['entity_type'], unique=False)

    op.create_table('notification_logs',
    sa.Column('notification_id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('channel', sa.String(length=20), nullable=False),
    sa.Column('recipient_snapshot', sa.JSON(none_as_null=True), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='prepared', nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("channel IN ('sms','email')", name='ck_notification_channel'),
    sa.CheckConstraint("status IN ('prepared','simulated','cancelled')", name='ck_notification_status'),
    sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['parent_id'], ['parents.parent_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('notification_id')
    )
    with op.batch_alter_table('notification_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_notification_logs_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_notification_logs_created_by'), ['created_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_notification_logs_parent_id'), ['parent_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_notification_logs_student_id'), ['student_id'], unique=False)

    op.create_table('parent_contact_logs',
    sa.Column('contact_id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('method', sa.String(length=20), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('result', sa.Text(), nullable=True),
    sa.Column('contacted_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('contact_person_name', sa.String(length=50), nullable=True),
    sa.Column('contact_person_phone', sa.String(length=30), nullable=True),
    sa.CheckConstraint("method IN ('phone','in_person','sms','email','other')", name='ck_parent_contacts_method'),
    sa.CheckConstraint("parent_id IS NOT NULL OR (contact_person_name IS NOT NULL AND length(trim(contact_person_name, char(9)||char(10)||char(11)||char(12)||char(13)||' ')) > 0)", name='ck_parent_contacts_explicit_name'),
    sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['parent_id'], ['parents.parent_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('contact_id')
    )
    with op.batch_alter_table('parent_contact_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_parent_contact_logs_contacted_at'), ['contacted_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_parent_contact_logs_created_by'), ['created_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_parent_contact_logs_parent_id'), ['parent_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_parent_contact_logs_student_id'), ['student_id'], unique=False)

    op.create_table('reward_records',
    sa.Column('record_id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('record_type', sa.String(length=20), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('occurred_on', sa.Date(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.CheckConstraint("record_type IN ('reward','punishment')", name='ck_reward_record_type'),
    sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('record_id')
    )
    with op.batch_alter_table('reward_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_reward_records_created_by'), ['created_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_reward_records_occurred_on'), ['occurred_on'], unique=False)
        batch_op.create_index(batch_op.f('ix_reward_records_student_id'), ['student_id'], unique=False)

    # ### end Alembic commands ###

    # Frozen guards are not detected by Alembic autogeneration.
    for statement in SQLITE_TRIGGERS.values():
        op.execute(statement)


def downgrade():
    for name in reversed(list(SQLITE_TRIGGERS)):
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('reward_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reward_records_student_id'))
        batch_op.drop_index(batch_op.f('ix_reward_records_occurred_on'))
        batch_op.drop_index(batch_op.f('ix_reward_records_created_by'))

    op.drop_table('reward_records')
    with op.batch_alter_table('parent_contact_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_parent_contact_logs_student_id'))
        batch_op.drop_index(batch_op.f('ix_parent_contact_logs_parent_id'))
        batch_op.drop_index(batch_op.f('ix_parent_contact_logs_created_by'))
        batch_op.drop_index(batch_op.f('ix_parent_contact_logs_contacted_at'))

    op.drop_table('parent_contact_logs')
    with op.batch_alter_table('notification_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notification_logs_student_id'))
        batch_op.drop_index(batch_op.f('ix_notification_logs_parent_id'))
        batch_op.drop_index(batch_op.f('ix_notification_logs_created_by'))
        batch_op.drop_index(batch_op.f('ix_notification_logs_created_at'))

    op.drop_table('notification_logs')
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_logs_entity_type'))
        batch_op.drop_index(batch_op.f('ix_audit_logs_entity_id'))
        batch_op.drop_index(batch_op.f('ix_audit_logs_created_at'))
        batch_op.drop_index(batch_op.f('ix_audit_logs_actor_user_id'))

    op.drop_table('audit_logs')
    with op.batch_alter_table('attendance_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_attendance_records_student_id'))
        batch_op.drop_index(batch_op.f('ix_attendance_records_recorded_by'))
        batch_op.drop_index(batch_op.f('ix_attendance_records_attendance_date'))

    op.drop_table('attendance_records')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_role_id'))

    op.drop_table('users')
    with op.batch_alter_table('parents', schema=None) as batch_op:
        batch_op.drop_index('uq_parents_primary_per_student', sqlite_where=sa.text('is_primary = 1'))
        batch_op.drop_index(batch_op.f('ix_parents_student_id'))

    op.drop_table('parents')
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_enrollments_student_id'))
        batch_op.drop_index(batch_op.f('ix_enrollments_semester'))
        batch_op.drop_index(batch_op.f('ix_enrollments_course_id'))

    op.drop_table('enrollments')
    with op.batch_alter_table('students', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_students_status'))
        batch_op.drop_index(batch_op.f('ix_students_class_id'))

    op.drop_table('students')
    with op.batch_alter_table('school_classes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_school_classes_homeroom_teacher_id'))

    op.drop_table('school_classes')
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_courses_teacher_id'))

    op.drop_table('courses')
    op.drop_table('teachers')
    op.drop_table('roles')
    # ### end Alembic commands ###
