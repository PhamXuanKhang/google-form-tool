import pytest
from app import create_app, StorageService
from tempfile import NamedTemporaryFile

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

@pytest.fixture
def temp_db():
    temp_file = NamedTemporaryFile(delete=False)
    with StorageService(temp_file.name) as db:
        yield db
