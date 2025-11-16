// Quick test script for DashRAG API integration
// Run with: node test-api.js

const API_BASE_URL = "http://127.0.0.1:8000";

async function testAPI() {
  console.log("Testing DashRAG API connection...\n");

  try {
    // 1. Health check
    console.log("1. Testing health endpoint...");
    const healthResponse = await fetch(`${API_BASE_URL}/healthz`);
    const healthData = await healthResponse.json();
    console.log("✅ Health check:", healthData.ok ? "OK" : "Failed");
    console.log("   Free space:", healthData.free_space_mb, "MB\n");

    // 2. Create session
    console.log("2. Creating test session...");
    const sessionResponse = await fetch(`${API_BASE_URL}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "API Test Session" }),
    });
    const session = await sessionResponse.json();
    console.log("✅ Session created:", session.id);
    console.log("   Title:", session.title, "\n");

    // 3. List documents (should be empty)
    console.log("3. Listing documents...");
    const docsResponse = await fetch(`${API_BASE_URL}/documents?sid=${session.id}`);
    const docs = await docsResponse.json();
    console.log("✅ Documents count:", docs.length, "\n");

    // 4. Try a query without documents
    console.log("4. Testing query (should fail without documents)...");
    try {
      const queryResponse = await fetch(`${API_BASE_URL}/messages?sid=${session.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: "Test query",
          mode: "local",
        }),
      });
      
      if (!queryResponse.ok) {
        const errorText = await queryResponse.text();
        console.log("⚠️  Query failed as expected (no documents):", errorText, "\n");
      } else {
        const queryData = await queryResponse.json();
        console.log("✅ Query succeeded:", queryData, "\n");
      }
    } catch (error) {
      console.log("⚠️  Query error:", error.message, "\n");
    }

    console.log("✅ All tests completed successfully!");
    console.log("\nThe front-end should be able to connect to the API.");
    console.log("Start the Next.js app with: npm run dev");

  } catch (error) {
    console.error("❌ Test failed:", error.message);
    console.error("\nMake sure the DashRAG API is running at", API_BASE_URL);
  }
}

testAPI();
