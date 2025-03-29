from pydantic import BaseModel


class UpdateExtractedData(BaseModel):
    data: dict