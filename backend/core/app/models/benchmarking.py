from datetime import datetime
from app.bicep_utils.models.ids_base import Alert
from sqlalchemy import Column, Float, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Base
from sqlalchemy.future import select


class BenchmarkingIntermediateResult(Base):
    __tablename__ = "benchmarking_intermediate_result"
    
    id = Column(Integer, primary_key=True, index=True)
    ensemble_name = Column(String(256))
    ensemble_uuid = Column(String(64))
    container_name = Column(String(128))
    start_time = Column(String(256))
    stop_time = Column(String(256))
    
async def get_all_intermediate_results_for_ensemble_and_id(db: AsyncSession, uuid: str, ensemble_name: str):
    stmt = select(BenchmarkingIntermediateResult).where(
                                                        BenchmarkingIntermediateResult.ensemble_name == ensemble_name and 
                                                        BenchmarkingIntermediateResult.ensemble_uuid == uuid
                                                    )
    result = await db.execute(stmt)
    return result.scalars().all()  
async def save_intermedaite_result(db: AsyncSession, intermediate_result: BenchmarkingIntermediateResult):
    db.add(intermediate_result)
    await db.commit() 
    await db.refresh(intermediate_result) 
    
class BenchmarkingResultTransferObject():
    def __init__(self, dataset_id: int, alerts: list[Alert], start_time: datetime, stop_time: datetime):
        self.dataset_id = dataset_id
        self.alerts = alerts
        self.start_time = start_time
        self.stop_time = stop_time
        self.runtime = (datetime.strptime(stop_time, "%d-%m-%Y %H:%M:%S.%f") - datetime.strptime(start_time, "%d-%m-%Y %H:%M:%S.%f")).total_seconds()
        
class BenchmarkingResult(Base):
    __tablename__ = "benchmarking_result"

    id = Column(Integer, primary_key=True, index=True)
    dataset_name = Column(String(256))
    ids_name = Column(String(256))
    ensembling_method = Column(String(256))
    configuration_name = Column(String(256))
    ruleset_name = Column(String(256))
    start_time = Column(String(256))
    stop_time = Column(String(256))
    runtime = Column(Float)
    prec = Column(Float)
    detection_rate = Column(Float)
    f1_score = Column(Float)
    acc = Column(Float)
    fpr = Column(Float)
    fnr = Column(Float)
    fdr = Column(Float)
    avg_cpu_usage = Column(Float)
    avg_memory_usage = Column(Float)
    resource_query_mode = Column(String(32))
    resource_query_targets = Column(Text)

async def add_benchmarking_result(db: AsyncSession, result: BenchmarkingResult):
    db.add(result)
    await db.commit() 
    await db.refresh(result)  
    
async def get_all_benchmarking_results(db: AsyncSession):
    stmt = select(BenchmarkingResult)
    result = await db.execute(stmt)
    return result.scalars().all()  


async def get_benchmarking_result_by_id(db: AsyncSession, result_id: int):
    stmt = select(BenchmarkingResult).where(BenchmarkingResult.id == result_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
