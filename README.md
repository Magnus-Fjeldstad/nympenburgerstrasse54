# Flask GitHub Pages

This project is a simple Flask application designed to be deployed on GitHub Pages. It serves a dynamic web page using Flask and Jinja2 templating.

## Project Structure

```
flask-github-pages
├── src
│   ├── app.py               # Main entry point of the Flask application
│   └── templates
│       └── index.html       # HTML structure for the main page
├── requirements.txt          # Lists dependencies for the Flask application
├── .github
│   └── workflows
│       └── deploy.yml       # GitHub Actions workflow for deployment
├── README.md                 # Documentation for the project
└── static
    └── style.css            # CSS styles for the application
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone https://github.com/yourusername/flask-github-pages.git
   cd flask-github-pages
   ```

2. **Install dependencies:**
   Make sure you have Python and pip installed. Then run:
   ```
   pip install -r requirements.txt
   ```

3. **Run the application:**
   Navigate to the `src` directory and run:
   ```
   python app.py
   ```
   The application will be available at `http://127.0.0.1:5000`.

## Usage

- Access the main page of the application by navigating to `http://127.0.0.1:5000` in your web browser.
- The application dynamically renders content using the data provided in the Flask routes.

## Deployment

This project includes a GitHub Actions workflow for automatic deployment to GitHub Pages. Make sure to configure the `deploy.yml` file with the appropriate settings for your repository.

## License

This project is licensed under the MIT License. See the LICENSE file for details.