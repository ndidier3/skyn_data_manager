# SDM Web Interface

A web-based interface for the Skyn Data Manager (SDM) application, providing a user-friendly way to run analyses and view results.

## Features

- **Analysis Setup**
  - Configure analysis settings with a user-friendly interface
  - Support for both single file and batch processing
  - Real-time validation of settings
  - Progress tracking for long-running analyses

- **Results Viewer**
  - Browse and search through processed studies
  - View detailed results for days, curves, and events
  - Interactive plots and data tables
  - Export results in various formats

## Prerequisites

- Node.js (v12 or later)
- npm (v6 or later)
- Python 3.8 or later
- PostgreSQL database

## Installation

1. Install frontend dependencies:
   ```bash
   cd App/SDM/web
   npm install
   ```

2. Set up environment variables:
   ```bash
   # Create a .env file in the web directory
   VUE_APP_API_URL=http://localhost:5000
   ```

3. Start the development server:
   ```bash
   npm run serve
   ```

## Development

- The frontend is built with Vue.js 2.x and uses Vuex for state management
- Bootstrap 4 is used for styling
- Axios is used for API communication

### Project Structure

```
web/
├── src/
│   ├── components/     # Reusable Vue components
│   ├── views/         # Page components
│   ├── store/         # Vuex store modules
│   ├── router/        # Vue Router configuration
│   ├── App.vue        # Root component
│   └── main.js        # Application entry point
├── public/            # Static assets
└── package.json       # Project dependencies
```

### Available Scripts

- `npm run serve` - Start development server
- `npm run build` - Build for production
- `npm run lint` - Lint and fix files

## API Endpoints

### Studies

- `GET /api/studies` - List all studies
- `GET /api/studies/:id` - Get study details
- `POST /api/studies` - Create new study
- `POST /api/studies/:id/process` - Process study data
- `GET /api/studies/:id/status` - Get processing status

### Results

- `GET /api/studies/:id/days` - Get day features
- `GET /api/studies/:id/curves` - Get curve features
- `GET /api/studies/:id/events` - Get event features

### Settings

- `GET /api/settings/default` - Get default settings
- `POST /api/settings/validate` - Validate custom settings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 