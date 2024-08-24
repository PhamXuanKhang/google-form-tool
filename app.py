from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from form_information import *
from main import Main

""" Build API """

# Build data structure for receiving from client to api
class FieldModel(BaseModel):
    xpath: str
    field_type: str
    value: str = None     

class PageModel(BaseModel):
    fields: list[FieldModel]

class FormModel(BaseModel):
    pages: list[PageModel]
    num_forms: int
    money: int
    links: str

# Convert API data to object with method
def convert_field_model_to_field(field_model: FieldModel) -> Field:
    return Field(
        xpath=field_model.xpath,
        field_type=field_model.field_type,
        value=field_model.value
    )

def convert_page_model_to_page(page_model: PageModel) -> Page:
    fields = [convert_field_model_to_field(field) for field in page_model.fields]
    return Page(fields=fields)

def convert_form_model_to_form(form_model: FormModel) -> Form:
    pages = [convert_page_model_to_page(page) for page in form_model.pages]
    return Form(
        pages=pages,
        num_forms=form_model.num_forms,
        links=form_model.links,
        money=form_model.money
    )

# Initialize app with FastAPI
app = FastAPI()

# Create an object for handle all of requests
fill_app = None

# Build endpoint to receive form
@app.post("/submit-form/")
async def submit_form(form_model: FormModel):
    global fill_app
    form = convert_form_model_to_form(form_model)
    fill_app = Main(form)

# Build endpoint to start fill form
@app.post("/start-fill/")
async def start_fill(background_tasks: BackgroundTasks):
    if fill_app:
        background_tasks.add_task(fill_app.start_fill)
    else:
        return {"error": "Form has not been submitted."}

# Build endpoint to stop fill
@app.patch("/stop-fill/")
async def stop_fill():
    if fill_app:
        fill_app.stop_fill()
    else:
        return {"error": "Form has not been submitted."}

# Build endpoint to continue fill
@app.post("/continue-fill/")
async def continue_fill(background_tasks: BackgroundTasks):
    if fill_app:
        background_tasks.add_task(fill_app.continue_fill)
    else:
        return {"error": "Form has not been submitted."}
    
# Build endpoint to return progress state
@app.get("/progress-fill")
async def progress_fill():
    if fill_app:
        return {"progress": fill_app.state_num/fill_app.form.num_forms, "state_num": fill_app.state_num, "time": fill_app.time, "money": fill_app.form.money}
    else:
        return {"error": "Form has not been submitted."}
    
# Build endpoint to change mode
@app.patch("/change-mode/")
async def change_mode(mode: str):
    if fill_app:
        fill_app.is_fair = (mode=="fair")
    
app.mount("/", StaticFiles(directory="static", html=True), name="static")