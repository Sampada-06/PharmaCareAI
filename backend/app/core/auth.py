from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .supabase_client import supabase

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validates the Supabase JWT token and returns the user object.
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase client not initialized"
        )

    token = credentials.credentials
    
    try:
        # Validate token using supabase.auth.get_user(token)
        # This validates the JWT and returns the user if valid
        response = supabase.auth.get_user(token)
        
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
            
        return response.user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

def get_user_profile(user_id: str):
    """
    Queries the 'profiles' table for user details.
    """
    if not supabase:
        return None

    try:
        # Query 'profiles' table
        response = supabase.table("profiles").select("full_name, phone, address, role").eq("id", user_id).single().execute()
        
        if hasattr(response, 'data') and response.data:
            return response.data
            
        return None
    except Exception as e:
        # Log error safely in a real app
        return None
