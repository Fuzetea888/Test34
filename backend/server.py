from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import bcrypt
import jwt
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Family Dom Maroc API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

# Enums
class UserType(str, Enum):
    CLIENT = "client"
    PROVIDER = "provider"

class ServiceCategory(str, Enum):
    MENAGE = "menage"
    GARDE_ENFANTS = "garde_enfants"  
    BRICOLAGE = "bricolage"
    JARDINAGE = "jardinage"
    SOUTIEN_SCOLAIRE = "soutien_scolaire"
    AIDE_SENIORS = "aide_seniors"

class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# User Models
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: str
    user_type: UserType
    city: str
    address: str
    profile_image: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    created_at: datetime
    is_verified: bool = False

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Service Provider Models
class ProviderProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    services: List[ServiceCategory]
    hourly_rate: Dict[ServiceCategory, float]
    experience_years: int
    description: str
    availability: Dict[str, List[str]]  # {"monday": ["09:00", "10:00", ...]}
    rating: float = 0.0
    total_reviews: int = 0
    is_verified: bool = False
    verification_documents: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProviderProfileCreate(BaseModel):
    services: List[ServiceCategory]
    hourly_rate: Dict[ServiceCategory, float]
    experience_years: int
    description: str
    availability: Dict[str, List[str]]

# Booking Models
class BookingCreate(BaseModel):
    provider_id: str
    service_category: ServiceCategory
    scheduled_date: datetime
    duration_hours: int
    address: str
    notes: Optional[str] = None

class Booking(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    provider_id: str
    service_category: ServiceCategory
    scheduled_date: datetime
    duration_hours: int
    address: str
    notes: Optional[str] = None
    status: BookingStatus = BookingStatus.PENDING
    total_price: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Utility functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = await db.users.find_one({"id": user_id})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return UserResponse(**user)

# Authentication Routes
@api_router.post("/auth/register", response_model=Token)
async def register_user(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create user
    user_dict = user_data.dict()
    user_dict.pop("password")
    user_dict["id"] = str(uuid.uuid4())
    user_dict["hashed_password"] = hashed_password
    user_dict["created_at"] = datetime.utcnow()
    user_dict["is_verified"] = False
    
    await db.users.insert_one(user_dict)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_dict["id"]}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(**user_dict)
    return Token(access_token=access_token, token_type="bearer", user=user_response)

@api_router.post("/auth/login", response_model=Token)
async def login_user(user_credentials: UserLogin):
    # Find user
    user = await db.users.find_one({"email": user_credentials.email})
    if not user or not verify_password(user_credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"]}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(**user)
    return Token(access_token=access_token, token_type="bearer", user=user_response)

# User Profile Routes
@api_router.get("/profile", response_model=UserResponse)
async def get_user_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user

@api_router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    updates: Dict[str, Any],
    current_user: UserResponse = Depends(get_current_user)
):
    # Remove sensitive fields
    updates.pop("id", None)
    updates.pop("hashed_password", None)
    updates.pop("created_at", None)
    
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": updates}
    )
    
    updated_user = await db.users.find_one({"id": current_user.id})
    return UserResponse(**updated_user)

# Provider Profile Routes
@api_router.post("/provider/profile", response_model=ProviderProfile)
async def create_provider_profile(
    profile_data: ProviderProfileCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.user_type != UserType.PROVIDER:
        raise HTTPException(status_code=403, detail="Only providers can create provider profiles")
    
    # Check if profile already exists
    existing_profile = await db.provider_profiles.find_one({"user_id": current_user.id})
    if existing_profile:
        raise HTTPException(status_code=400, detail="Provider profile already exists")
    
    profile_dict = profile_data.dict()
    profile_dict["id"] = str(uuid.uuid4())
    profile_dict["user_id"] = current_user.id
    profile_dict["created_at"] = datetime.utcnow()
    profile_dict["rating"] = 0.0
    profile_dict["total_reviews"] = 0
    profile_dict["is_verified"] = False
    profile_dict["verification_documents"] = []
    
    await db.provider_profiles.insert_one(profile_dict)
    return ProviderProfile(**profile_dict)

@api_router.get("/provider/profile", response_model=ProviderProfile)
async def get_provider_profile(current_user: UserResponse = Depends(get_current_user)):
    if current_user.user_type != UserType.PROVIDER:
        raise HTTPException(status_code=403, detail="Only providers can access provider profiles")
    
    profile = await db.provider_profiles.find_one({"user_id": current_user.id})
    if not profile:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    
    return ProviderProfile(**profile)

@api_router.get("/providers", response_model=List[Dict[str, Any]])
async def get_all_providers(
    service: Optional[ServiceCategory] = None,
    city: Optional[str] = None,
    limit: int = 20
):
    # Build query
    query = {}
    if service:
        query["services"] = service
    
    # Get provider profiles
    provider_profiles = await db.provider_profiles.find(query).limit(limit).to_list(limit)
    
    # Get user data for each provider
    results = []
    for profile in provider_profiles:
        user = await db.users.find_one({"id": profile["user_id"]})
        if user and (not city or user.get("city", "").lower() == city.lower()):
            result = {
                "provider_profile": ProviderProfile(**profile),
                "user_info": {
                    "full_name": user["full_name"],
                    "city": user["city"],
                    "profile_image": user.get("profile_image")
                }
            }
            results.append(result)
    
    return results

# Booking Routes
@api_router.post("/bookings", response_model=Booking)
async def create_booking(
    booking_data: BookingCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.user_type != UserType.CLIENT:
        raise HTTPException(status_code=403, detail="Only clients can create bookings")
    
    # Get provider profile to calculate price
    provider_profile = await db.provider_profiles.find_one({"user_id": booking_data.provider_id})
    if not provider_profile:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Calculate total price
    hourly_rate = provider_profile["hourly_rate"].get(booking_data.service_category, 0)
    total_price = hourly_rate * booking_data.duration_hours
    
    booking_dict = booking_data.dict()
    booking_dict["id"] = str(uuid.uuid4())
    booking_dict["client_id"] = current_user.id
    booking_dict["status"] = BookingStatus.PENDING
    booking_dict["total_price"] = total_price
    booking_dict["created_at"] = datetime.utcnow()
    booking_dict["updated_at"] = datetime.utcnow()
    
    await db.bookings.insert_one(booking_dict)
    return Booking(**booking_dict)

@api_router.get("/bookings", response_model=List[Booking])
async def get_user_bookings(current_user: UserResponse = Depends(get_current_user)):
    if current_user.user_type == UserType.CLIENT:
        bookings = await db.bookings.find({"client_id": current_user.id}).to_list(100)
    else:  # PROVIDER
        bookings = await db.bookings.find({"provider_id": current_user.id}).to_list(100)
    
    return [Booking(**booking) for booking in bookings]

@api_router.put("/bookings/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    status: BookingStatus,
    current_user: UserResponse = Depends(get_current_user)
):
    booking = await db.bookings.find_one({"id": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Check permissions
    if current_user.user_type == UserType.CLIENT and booking["client_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this booking")
    elif current_user.user_type == UserType.PROVIDER and booking["provider_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this booking")
    
    await db.bookings.update_one(
        {"id": booking_id},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}}
    )
    
    return {"message": "Booking status updated successfully"}

# Health check
@api_router.get("/")
async def root():
    return {"message": "Family Dom Maroc API", "status": "running"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()