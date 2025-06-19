# UAV Log Viewer Backend

This is the backend API for the UAV Log Viewer application, providing RESTful endpoints for log file processing and an AI-powered chatbot for UAV log analysis.

## Features

- **RESTful API**: Handle log file uploads and processing
- **AI Chatbot**: Intelligent analysis of UAV log files using natural language processing
- **File Management**: Secure handling of uploaded log files
- **Real-time Processing**: Efficient log parsing and analysis

## Project Structure

```
backend/
├── api.py              # Main Flask API endpoints
├── chatbot.py          # AI chatbot implementation
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not tracked)
├── .gitignore         # Git ignore rules
└── uploaded_logs/     # Directory for uploaded files (not tracked)
```

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/chandu-aravapalli/UAVLogViewer.git
   cd UAVLogViewer/backend
   ```

2. **Create a virtual environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the backend directory:
   ```env
   FLASK_APP=api.py
   FLASK_ENV=development
   ```

## Usage

### Starting the API Server

```bash
# Activate virtual environment
source venv/bin/activate

# Run the Flask application
python api.py
```

The API will be available at `http://localhost:5000`

### API Endpoints

#### 1. Health Check

- **GET** `/health`
- Returns server status

#### 2. File Upload

- **POST** `/upload`
- Upload UAV log files for processing
- Accepts multipart form data

#### 3. Chatbot Interface

- **POST** `/chat`
- Send messages to the AI chatbot
- Request body: `{"message": "your question about the log file"}`
- Returns AI-generated responses

## Dependencies

The main dependencies include:

- **Flask**: Web framework for the API
- **OpenAI**: AI chatbot integration
- **Pandas**: Data processing for log files
- **NumPy**: Numerical computations
- **Requests**: HTTP library for external API calls

See `requirements.txt` for the complete list.

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
FLASK_APP=api.py
FLASK_ENV=development
OPENAI_API_KEY=your_openai_api_key_here
```

### API Configuration

The API is configured to:

- Accept file uploads up to 16MB
- Store uploaded files in `uploaded_logs/` directory
- Process UAV log files in various formats
- Provide real-time chatbot responses

## Development

### Running in Development Mode

```bash
export FLASK_ENV=development
export FLASK_APP=api.py
flask run
```

### Testing

To test the API endpoints:

1. **Health Check**:

   ```bash
   curl http://localhost:5000/health
   ```

2. **File Upload**:

   ```bash
   curl -X POST -F "file=@your_log_file.log" http://localhost:5000/upload
   ```

3. **Chatbot**:
   ```bash
   curl -X POST -H "Content-Type: application/json" \
        -d '{"message":"What does this log file show?"}' \
        http://localhost:5000/chat
   ```

## Security Considerations

- Uploaded files are stored in a secure directory
- File size limits are enforced
- Environment variables are used for sensitive data
- Input validation is implemented for all endpoints

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the GPL-3.0 license - see the [LICENSE](../LICENSE) file for details.

## Support

For issues and questions:

- Create an issue on GitHub
- Check the frontend documentation for integration details
- Review the API endpoints documentation above

## Related Projects

- **Frontend**: [UAVLogViewer Frontend](../) - Vue.js web application
- **Main Repository**: [UAVLogViewer](https://github.com/chandu-aravapalli/UAVLogViewer)
