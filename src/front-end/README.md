# DashRAG Frontend

A chat interface for the DashRAG system built with Next.js, TypeScript, and Tailwind CSS.

Built for ECE496 Capstone Project, 2025-2026

Based on [Chatbot UI Lite](https://github.com/mckaywrigley/chatbot-ui-lite.git) by Mckay Wrigley.

## Features

DashRAG Frontend provides a clean, functional chat interface for interacting with the DashRAG backend API.

Key components:
- Chat interface in `components/Chat`
- API integration in `utils/dashrag-api.ts`
- Session management with `utils/useSessionManager.ts`

## Running Locally

**1. Install Dependencies**

```bash
npm i
```

**2. Run Development Server**

```bash
npm run dev
```

**3. Start Building**

The app will be available at `http://localhost:3000`. The frontend connects to the DashRAG backend API for chat functionality.
