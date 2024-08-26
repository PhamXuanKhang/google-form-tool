# Sử dụng image python slim 3.9 làm base
FROM python:3.9-slim

# Cài đặt các thư viện hệ thống và Google Chrome
RUN apt-get update && \
    apt-get install -y wget unzip libx11-dev libxkbcommon-x11-0 libnss3 libgbm1 \
                       fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
                       libatspi2.0-0 libcairo2 libcups2 libcurl3-gnutls libcurl3-nss \
                       libcurl4 libdbus-1-3 libglib2.0-0 libgtk-3-0 libgtk-4-1 \
                       libpango-1.0-0 libvulkan1 libxcomposite1 libxdamage1 libxext6 \
                       libxfixes3 libxrandr2 xdg-utils && \
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    dpkg -i google-chrome-stable_current_amd64.deb || apt-get -f install -y && \
    rm google-chrome-stable_current_amd64.deb && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Tải và cài đặt ChromeDriver tương thích với phiên bản Chrome hiện tại
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+\.\d+') && \
    CHROME_DRIVER_VERSION=$(wget -qO- https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION) && \
    wget -q https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip && \
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
