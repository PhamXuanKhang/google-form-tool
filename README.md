# Google Form Automation Tool

A powerful web-based automation tool for extracting, processing, and submitting Google Forms using Flask and Selenium. This tool provides a user-friendly interface to automate form interactions, making it easy to handle bulk submissions and form data extraction.

## Features

- 🔍 **Form Extraction**: Extract form structure and questions from Google Forms URLs
- 📝 **Automated Submission**: Bulk submit forms with custom data
- 🤖 **AI Response Generation**: Generate intelligent responses for form fields
- 📊 **Data Management**: Load and manage form data from files
- 🌐 **Multi-language Support**: English and Vietnamese language support
- 📈 **Real-time Monitoring**: Monitor CPU, network, and submission metrics
- 💾 **Data Persistence**: Store form configurations and submission history
- 🎨 **Web Interface**: Clean and intuitive web-based user interface

## Tech Stack

- **Backend**: Flask 3.1.0
- **Automation**: Selenium 4.32.0
- **Database**: TinyDB 4.8.2
- **Internationalization**: Flask-Babel 4.0.0
- **Environment**: Python-dotenv 1.1.0
- **Browser**: Chrome/Chromium with ChromeDriver

## Project Structure

```
google_form_automation_tool/
├── app/
│   ├── core/
│   │   ├── form_extractor.py      # Form data extraction logic
│   │   ├── form_processor.py      # Form processing utilities
│   │   ├── form_submitter.py      # Form submission automation
│   │   └── webview_manager.py     # Web view management
│   ├── monitoring/
│   │   ├── cpu_monitor.py         # CPU usage monitoring
│   │   ├── metrics_collector.py   # System metrics collection
│   │   └── network_monitor.py     # Network monitoring
│   ├── __init__.py               # Flask app factory
│   ├── main_routes.py            # Main application routes
│   └── models.py                 # Data models
├── translations/                 # Internationalization files
├── drivers/                      # Browser drivers
├── docs/                         # Documentation
├── templates/                    # HTML templates
├── static/                       # Static assets (CSS, JS, images)
├── app.py                        # Application entry point
├── config.py                     # Configuration settings
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables
└── README.md                     # This file
```

## Installation

### Prerequisites

- Python 3.8 or higher
- Google Chrome or Chromium browser
- ChromeDriver (compatible with your Chrome version)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd google_form_automation_tool
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

5. **Download ChromeDriver**
   - Download ChromeDriver from [official site](https://chromedriver.chromium.org/)
   - Place it in the `drivers/` directory
   - Make sure it's executable

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   - Open your browser and go to `http://localhost:5000`

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
SECRET_KEY=your-secret-key-here
DB_PATH=app/services/db.json
FLASK_ENV=development
FLASK_DEBUG=True
```

### Chrome Options

The application uses headless Chrome by default with the following options:
- `--no-sandbox`
- `--disable-dev-shm-usage`
- `--disable-extensions`
- `--disable-gpu`
- `--disable-notifications`
- `--log-level=3`
- `--headless`

## Usage

### 1. Extract Form Data

1. Navigate to the "Form Filling" page
2. Enter the Google Form URL
3. Click "Extract" to analyze the form structure
4. The tool will extract all questions, field types, and options

### 2. Load Data File

1. Prepare your data in a compatible format (CSV, JSON)
2. Upload the file through the web interface
3. Map the data fields to form questions

### 3. Generate AI Responses

1. Configure AI response settings
2. Generate intelligent responses for form fields
3. Review and edit responses as needed

### 4. Start Automation

1. Configure submission settings
2. Set delays and batch sizes
3. Start the automated submission process
4. Monitor progress in real-time

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Home page with recent forms |
| GET | `/form_filling` | Form filling interface |
| GET | `/about` | About page |
| POST | `/extract` | Extract form data from URL |
| POST | `/load_data` | Load data from file |
| POST | `/generate_response` | Generate AI responses |
| POST | `/save_edit` | Save form configuration |
| POST | `/start_submission` | Start submission process |
| POST | `/stop_submission` | Stop submission process |
| GET | `/submission_status` | Get submission status |
| GET | `/setlang` | Set language preference |

## Development

### Running in Development Mode

```bash
export FLASK_ENV=development
export FLASK_DEBUG=True
python app.py
```

### Code Style

The project follows PEP 8 guidelines. Use tools like `flake8` or `black` for code formatting:

```bash
pip install black flake8
black .
flake8 .
```

### Testing

```bash
# Install test dependencies
pip install pytest pytest-flask

# Run tests
pytest
```

### Internationalization

To add new translations:

```bash
# Extract messages
pybabel extract -F babel.cfg -k _l -o messages.pot .

# Update existing translations
pybabel update -i messages.pot -d translations

# Compile translations
pybabel compile -d translations
```

## Docker Support

Build and run with Docker:

```bash
# Build image
docker build -t google-form-automation .

# Run container
docker run -p 5000:5000 google-form-automation
```

## Monitoring

The application includes built-in monitoring for:
- CPU usage
- Network activity
- Memory consumption
- Submission metrics
- Error tracking

## Troubleshooting

### Common Issues

1. **ChromeDriver not found**
   - Ensure ChromeDriver is in the `drivers/` directory
   - Check that the ChromeDriver version matches your Chrome version

2. **Permission denied errors**
   - Make sure ChromeDriver has execute permissions
   - Run: `chmod +x drivers/chromedriver`

3. **Form extraction fails**
   - Verify the Google Form URL is accessible
   - Check if the form requires authentication
   - Ensure the form is publicly accessible

4. **Slow performance**
   - Adjust batch sizes for submissions
   - Increase delays between requests
   - Monitor system resources

### Logs

Check application logs for detailed error information:
- Flask logs: Console output
- Selenium logs: Browser console
- Application logs: Check the logs directory

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Security Considerations

- Always use HTTPS in production
- Keep your secret key secure
- Validate all form inputs
- Implement rate limiting for API endpoints
- Use environment variables for sensitive data
- Regularly update dependencies

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the documentation in the `docs/` directory
- Review the troubleshooting section above

## Roadmap

- [ ] Advanced form field detection
- [ ] Integration with external APIs
- [ ] Enhanced AI response generation
- [ ] Real-time dashboard
- [ ] Scheduled submissions
- [ ] Export/import configurations
- [ ] Advanced analytics

---

**Note**: This tool is for educational and legitimate automation purposes only. Please respect Google's Terms of Service and use responsibly.
