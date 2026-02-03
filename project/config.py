import os

class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PASSWORD_MIN_LENGTH = int(os.environ.get("PASSWORD_MIN_LENGTH", 8))
    REQUIRE_STRONG_PASSWORD = os.environ.get("REQUIRE_STRONG_PASSWORD", "true").lower() in ("1","true","yes","on")
    SESSION_TIMEOUT_MINUTES = int(os.environ.get("SESSION_TIMEOUT_MINUTES", 120))
    ALLOW_SELF_REGISTRATION = os.environ.get("ALLOW_SELF_REGISTRATION", "true").lower() in ("1","true","yes","on")
    PASSWORD_RESET_ENABLED = os.environ.get("PASSWORD_RESET_ENABLED", "true").lower() in ("1","true","yes","on")
    MAX_BULK_IMPORT_ROWS = int(os.environ.get("MAX_BULK_IMPORT_ROWS", 1000))
    # Scheduling & Timetabling governance
    TEACHER_MAX_SESSIONS_PER_DAY = int(os.environ.get("TEACHER_MAX_SESSIONS_PER_DAY", 4))
    TEACHER_MAX_SESSIONS_PER_WEEK = int(os.environ.get("TEACHER_MAX_SESSIONS_PER_WEEK", 20))
    COURSE_MAX_SESSIONS_PER_WEEK = int(os.environ.get("COURSE_MAX_SESSIONS_PER_WEEK", 10))
    COURSE_REQUIRE_CREDITS = os.environ.get("COURSE_REQUIRE_CREDITS", "false").lower() in ("1","true","yes","on")
    LAB_SESSION_KEYWORD = os.environ.get("LAB_SESSION_KEYWORD", "Lab")
    LAB_MIN_SPACING_DAYS = int(os.environ.get("LAB_MIN_SPACING_DAYS", 3))
    LAB_GENERATE_EVERY_N = int(os.environ.get("LAB_GENERATE_EVERY_N", 0))
    PROJECT_SESSION_KEYWORD = os.environ.get("PROJECT_SESSION_KEYWORD", "Project")
    PROJECT_MIN_SPACING_DAYS = int(os.environ.get("PROJECT_MIN_SPACING_DAYS", 7))
    PROJECT_GENERATE_EVERY_M = int(os.environ.get("PROJECT_GENERATE_EVERY_M", 0))
    # Attendance governance
    ATTENDANCE_MARKING_CUTOFF_DAYS = int(os.environ.get("ATTENDANCE_MARKING_CUTOFF_DAYS", 30))
    ATTENDANCE_ALLOW_EDIT = os.environ.get("ATTENDANCE_ALLOW_EDIT", "true").lower() in ("1","true","yes","on")
    # Timetable hour caps (approximate without per-session times)
    SESSION_DEFAULT_DURATION_HOURS = int(os.environ.get("SESSION_DEFAULT_DURATION_HOURS", 1))
    TEACHER_MAX_HOURS_PER_DAY = int(os.environ.get("TEACHER_MAX_HOURS_PER_DAY", 6))
    TEACHER_MAX_HOURS_PER_WEEK = int(os.environ.get("TEACHER_MAX_HOURS_PER_WEEK", 30))
    HOURS_PER_CREDIT = int(os.environ.get("HOURS_PER_CREDIT", 15))
    # Faculty & Staff Management governance
    WORKLOAD_FAIRNESS_ENABLED = os.environ.get("WORKLOAD_FAIRNESS_ENABLED", "true").lower() in ("1","true","yes","on")
    WORKLOAD_TARGET_WEEKLY_HOURS = int(os.environ.get("WORKLOAD_TARGET_WEEKLY_HOURS", 24))
    WORKLOAD_TOLERANCE_HOURS = int(os.environ.get("WORKLOAD_TOLERANCE_HOURS", 4))
    ALLOW_WEEKEND_SESSIONS = os.environ.get("ALLOW_WEEKEND_SESSIONS", "false").lower() in ("1","true","yes","on")
    LEAVE_APPROVAL_REQUIRED = os.environ.get("LEAVE_APPROVAL_REQUIRED", "true").lower() in ("1","true","yes","on")
    PERFORMANCE_ENABLED = os.environ.get("PERFORMANCE_ENABLED", "true").lower() in ("1","true","yes","on")
    PERFORMANCE_MIN_SESSIONS_FOR_REPORT = int(os.environ.get("PERFORMANCE_MIN_SESSIONS_FOR_REPORT", 5))
    # Finance
    DEFAULT_CURRENCY = os.environ.get("DEFAULT_CURRENCY", "USD")
    FINANCE_ALLOW_PARTIAL_PAYMENTS = os.environ.get("FINANCE_ALLOW_PARTIAL_PAYMENTS", "true").lower() in ("1","true","yes","on")
    TAX_RATE_PERCENT = float(os.environ.get("TAX_RATE_PERCENT", 0.0))
    DISCOUNT_MAX_PERCENT = float(os.environ.get("DISCOUNT_MAX_PERCENT", 0.0))
    # Resources
    MAX_BOOKING_DURATION_MINUTES = int(os.environ.get("MAX_BOOKING_DURATION_MINUTES", 240))
    RESOURCE_AUTO_APPROVE_ROLES = os.environ.get("RESOURCE_AUTO_APPROVE_ROLES", "admin")
    ADMISSION_PHOTOS_DIR = os.environ.get(
        "ADMISSION_PHOTOS_DIR",
        os.path.join(os.path.dirname(__file__), "static", "uploads", "admissions")
    )
    USER_AVATARS_DIR = os.environ.get(
        "USER_AVATARS_DIR",
        os.path.join(os.path.dirname(__file__), "static", "uploads", "avatars")
    )

class DevelopmentConfig(BaseConfig):
    # Default to instance/site.db unless overridden
    INSTANCE_PATH = os.environ.get("FLASK_INSTANCE_PATH")
    @staticmethod
    def database_uri(instance_path: str) -> str:
        db_path = os.environ.get("DATABASE_PATH")
        if db_path:
            return f"sqlite:///{db_path}"
        return "sqlite:///" + os.path.join(instance_path, "site.db")

class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URI", "sqlite:///:memory:")

class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI", "sqlite:///site.db")
