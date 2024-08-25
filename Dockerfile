# Sử dụng image python slim 3.9 làm base
FROM python:3.9-slim

# Cài đặt các thư viện hệ thống cần thiết
RUN apt-get update && \
    apt-get install -y \
    wget \
    unzip \
    libx11-dev \
    libxkbcommon-x11-0 \
    libnss3 \
    libgbm1 \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Cài đặt Chromium
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    dpkg -i google-chrome-stable_current_amd64.deb && \
    apt-get -f install -y && \
    rm google-chrome-stable_current_amd64.deb

# Tải và cài đặt ChromeDriver
RUN CHROME_DRIVER_VERSION=$(wget -qO- https://chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
    wget https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip && \
    mv chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm chromedriver_linux64.zip

# Đặt thư mục làm việc
WORKDIR /app

# Sao chép file requirements.txt vào container
COPY requirements.txt .

# Cài đặt các thư viện Python cần thiết
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn vào container
COPY . .

# Chạy ứng dụng FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]