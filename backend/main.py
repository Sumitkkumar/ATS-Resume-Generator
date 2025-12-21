
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from agent import JobResumeAgent, JobResumeAgentConfig
from jd_scraper import scrape_jd
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Req(BaseModel):
    jd_text: str
    grey_hat: bool = True

class JDUrlRequest(BaseModel):
    jd_url: str
    grey_hat: bool = True

@app.post("/generate-resume")
async def gen(req: Req):
    agent = JobResumeAgent(config=JobResumeAgentConfig(grey_hat=req.grey_hat))
    pdf = agent.generate(req.jd_text)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=resume.pdf"}
    )

@app.post("/generate-resume-from-url")
async def gen_from_url(req: JDUrlRequest):
    try:
        jd_text = scrape_jd(req.jd_url)
        agent = JobResumeAgent(
            config=JobResumeAgentConfig(grey_hat=req.grey_hat)
        )
        pdf = agent.generate(jd_text)

        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=resume.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
