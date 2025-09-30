from pydantic import BaseModel
from typing import Optional, List, Dict

class PredictRequest(BaseModel):
    target: str
    id: str

class DataSourceCredentials(BaseModel):
    meta_ads: Optional[Dict[str, str]] = None
    google_ads: Optional[Dict[str, str]] = None
    ga4: Optional[Dict[str, str]] = None

class PredictWithDataRequest(BaseModel):
    target: str
    id: str
    use_external_data: Optional[bool] = False
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    data_sources: Optional[List[str]] = None
    merge_on: Optional[str] = None

class ConfigureDataSourceRequest(BaseModel):
    user_id: str
    credentials: DataSourceCredentials

class LoadUserCredentialsRequest(BaseModel):
    user_id: str

class PredictWithUserDataRequest(BaseModel):
    user_id: str
    target: str
    id: str
    use_external_data: Optional[bool] = False
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    data_sources: Optional[List[str]] = None
    merge_on: Optional[str] = None

