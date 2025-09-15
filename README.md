# NDA Redline - AI-Powered NDA Redlining

Minimal, trustworthy NDA redlining web app with AI assistance.

## Quickstart

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for local dev)
- Python 3.11+ (for local dev)
- OpenAI API key (for AI redlining features)

### Setup
1. Clone and setup environment:
```bash
git clone <repo-url>
cd nda-project
cp api/.env.sample api/.env
cp web/.env.local.example web/.env.local
# Edit .env files with your values
# Add your OpenAI API key to api/.env
```

2. Start services:
```bash
make up
```

3. Run database migrations:
```bash
make reset-db
```

4. Verify:
- Web: http://localhost:3000
- API: http://localhost:5001/healthz
- Database: localhost:5432

### Development
```bash
make up          # Start all services
make down        # Stop all services
make logs        # View logs
make reset-db    # Reset database and run migrations
```

### Testing AI Integration
```bash
cd api
python test_ai_integration.py
```

### Smoke Test
```bash
curl http://localhost:5001/healthz
# Should return: {"status":"ok"}
```

## Architecture
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Backend**: Flask, SQLAlchemy, PostgreSQL
- **AI**: OpenAI GPT-4 integration for intelligent document redlining
- **Document Processing**: Python-docx for Word document manipulation
- **Hosting**: Railway (target)

## AI Redlining Features

### OpenAI GPT-4 Integration
- **Intelligent Analysis**: GPT-4 analyzes NDA documents and identifies areas for modification
- **Custom Rules Engine**: Define specific redlining instructions (term limits, party inclusion, etc.)
- **Structured Output**: AI returns specific modification instructions in JSON format
- **Legal Compliance**: AI ensures modifications maintain legal validity

### Document Processing Engine
- **Word Document Support**: Upload .docx files for processing
- **Tracked Changes**: Apply modifications with professional redlining formatting
- **Firm Details Integration**: Automatic insertion of firm information and signature blocks
- **Batch Processing**: Handle multiple documents with consistent rule application

### Processing Rules
- **Term Duration**: Cap confidentiality obligations at specified limits
- **Party Management**: Ensure key parties (investors, agents) are included
- **Liability Clauses**: Optimize liability and damage limitation terms
- **Firm Information**: Standardize firm details across all documents

## API Endpoints

### Documents
- `POST /v1/documents/upload` - Upload NDA document
- `POST /v1/documents/{id}/process` - Process document with AI redlining
- `GET /v1/documents/{id}` - Get document details
- `GET /v1/documents/` - List user documents
- `DELETE /v1/documents/{id}` - Delete document

### Processing Rules
- `GET /v1/rules/` - List user rules
- `POST /v1/rules/` - Create new rule
- `PUT /v1/rules/{id}` - Update rule
- `DELETE /v1/rules/{id}` - Delete rule
- `GET /v1/rules/categories` - Get rule categories
- `GET /v1/rules/templates` - Get predefined rule templates

## Security Features
- JWT stored in httpOnly cookies
- CORS restricted to web origin
- Input validation on all endpoints
- File upload size limits enforced
- Document retention policies (24-hour automatic cleanup)
- No AI model training on user documents

## Environment Variables

### Backend (.env)
```bash
FLASK_APP=run.py
FLASK_ENV=development
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/nda_redline
JWT_SECRET=your-super-secret-jwt-key-change-in-production
CORS_ORIGIN=http://localhost:3000
OPENAI_API_KEY=your-openai-api-key
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:5001
```

## Database Schema

### Core Tables
- **users**: User authentication and profile information
- **documents**: NDA document storage and metadata
- **processing_rules**: Custom redlining rules and instructions
- **processing_jobs**: Document processing job tracking

### Document Status Flow
1. **uploaded**: Document uploaded, ready for processing
2. **processing**: AI analysis and redlining in progress
3. **completed**: Document processed successfully
4. **error**: Processing failed with error details

## Development Workflow

### Adding New Processing Rules
1. Define rule in `ProcessingRule` model
2. Implement rule logic in `DocumentProcessor`
3. Add rule validation in API endpoints
4. Update frontend rule management interface

### Extending AI Capabilities
1. Modify prompts in `AIRedliningService`
2. Add new modification types to document processor
3. Update frontend to handle new AI features
4. Test with various document types

### Testing
- Run `python test_ai_integration.py` to test AI service
- Use demo page for end-to-end testing
- Check API endpoints with tools like Postman
- Monitor logs with `make logs`

## Production Considerations

### Performance
- Implement document processing queues for high-volume usage
- Add caching for frequently used rules and templates
- Optimize database queries with proper indexing

### Security
- Implement proper JWT validation middleware
- Add rate limiting for API endpoints
- Secure file upload validation and sanitization
- Monitor for suspicious AI usage patterns

### Scalability
- Use Redis for session management
- Implement horizontal scaling for document processing
- Add CDN for document delivery
- Consider microservices architecture for high-scale deployments
# Deployment test
