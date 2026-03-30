const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = process.env.PORT || 3000;

const storage = multer.diskStorage({
  destination: 'uploads/',
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname);
    cb(null, `${Date.now()}-${uuidv4()}${ext}`);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: 5 * 1024 * 1024 }
});

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

app.post('/feedback', (req, res, next) => {
  upload.single('attachment')(req, res, (err) => {
    if (err && err.code === 'LIMIT_FILE_SIZE') {
      return res.status(400).json({ error: 'File size exceeds 5MB limit' });
    }
    if (err) return next(err);

    const { issueType, details } = req.body;

    if (!issueType) {
      return res.status(400).json({ error: 'Issue type is required' });
    }

    const entry = {
      id: uuidv4(),
      timestamp: new Date().toISOString(),
      issueType,
      details: details || '',
      attachmentPath: req.file ? path.join('uploads', req.file.filename) : null
    };

    const feedbackPath = path.join(__dirname, 'data', 'feedback.json');
    let feedbackData = [];
    if (fs.existsSync(feedbackPath)) {
      try {
        feedbackData = JSON.parse(fs.readFileSync(feedbackPath, 'utf8'));
      } catch (e) {
        feedbackData = [];
      }
    }
    feedbackData.push(entry);
    fs.writeFileSync(feedbackPath, JSON.stringify(feedbackData, null, 2));

    res.json({ success: true, id: entry.id });
  });
});

const server = app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});

module.exports = { app, server };
