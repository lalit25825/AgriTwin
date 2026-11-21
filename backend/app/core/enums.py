from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    FARMER = "farmer"
    DRIVER = "driver"
    STORAGE_OWNER = "storage_owner"
    MANDI_SELLER = "mandi_seller"
    MANDI_OWNER = "mandi_owner"
    FPO_MANAGER = "fpo_manager"
    # Legacy values remain valid for accounts created by earlier AgriTwin builds.
    BUYER = "buyer"
    FPO = "fpo"
    TRANSPORTER = "transporter"
    STORAGE_PROVIDER = "storage_provider"


class AuthProvider(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"
