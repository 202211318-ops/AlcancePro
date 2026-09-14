from .config import settings
from .models import AppSettings, User
from .security import hash_password

SEED_USERS = [
    {
        "name": "Administrador AlcancePro",
        "email": "admin@alcancepro.pe",
        "password": "Admin123*",
        "role": "ADMIN",
    },
    {
        "name": "Analista de Alcance",
        "email": "analista@alcancepro.pe",
        "password": "Admin123*",
        "role": "ANALISTA",
    },
    {
        "name": "Revisor Contractual",
        "email": "revisor@alcancepro.pe",
        "password": "Admin123*",
        "role": "REVISOR",
    },
]


async def seed_users() -> None:
    for item in SEED_USERS:
        existing = await User.find_one(User.email == item["email"])
        if existing:
            continue
        user = User(
            name=item["name"],
            email=item["email"],
            password_hash=hash_password(item["password"]),
            role=item["role"],
            is_active=True,
        )
        await user.insert()


async def sync_llm_settings() -> None:
    stored = await AppSettings.find_one(AppSettings.key == "global")
    if not stored:
        stored = AppSettings(
            key="global",
            llm_api_key=settings.llm_api_key,
            llm_base_url=settings.llm_base_url,
            llm_model=settings.llm_model,
        )
        await stored.insert()
        return
    if settings.llm_api_key:
        stored.llm_api_key = settings.llm_api_key
        stored.llm_base_url = settings.llm_base_url
        stored.llm_model = settings.llm_model
        await stored.save()
