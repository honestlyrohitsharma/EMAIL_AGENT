async function callGemini(prompt) {
    // Get the key from Chrome's storage
    const storageData = await chrome.storage.sync.get('geminiApiKey');
    const API_KEY = storageData.geminiApiKey;

    // Check if the key exists
    if (!API_KEY) {
        alert('API Key not found. Please set it in the extension popup.');
        return "Error: API Key not set.";
    }

    const API_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${API_KEY}`;
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ "contents": [{"parts": [{"text": prompt}]}] })
        });

        const data = await response.json();
        
        if (data.error) {
            console.error('Gemini API Error:', data.error.message);
            return `Error from Gemini: ${data.error.message}`;
        }
        return data.candidates[0].content.parts[0].text;
    } catch (error) {
        console.error("Failed to call Gemini API:", error);
        return "Failed to connect to the AI service.";
    }
}

function addAiButtons() {
    // A list of possible selectors for the bottom toolbar.
    const toolbarSelectors = [
        'div.amn',          // The selector that worked before
        'div.h7.h-Z-b-n'    // A previous selector, as a fallback
    ];

    let bottomBar = null;
    for (const selector of toolbarSelectors) {
        bottomBar = document.querySelector(selector);
        if (bottomBar) break; // Found one, stop looking.
    }

    // Proceed only if we found a toolbar and the button isn't already there
    if (bottomBar && !bottomBar.querySelector('.gemini-button')) {
        const summarizeButton = document.createElement('button');
        summarizeButton.innerText = '✨ Summarize';
        summarizeButton.className = 'gemini-button';
        summarizeButton.style.cssText = 'background-color: #1a73e8; color: white; border: none; padding: 10px 16px; margin-right: 16px; border-radius: 18px; cursor: pointer; font-weight: bold; vertical-align: middle;';

        summarizeButton.addEventListener('click', async (event) => {
            event.stopPropagation();
            
            // A list of possible selectors for the email body itself.
            const bodySelectors = [
                'div.a3s.aXjCH',    // A specific, often correct selector
                'div.gs',           // A common container for the whole email
                '.a3s'              // A more general, but often correct selector
            ];

            let emailBodyElement = null;
            for (const selector of bodySelectors) {
                emailBodyElement = document.querySelector(selector);
                if (emailBodyElement) break; // Found one, stop looking.
            }
            
            if (emailBodyElement) {
                const emailBody = emailBodyElement.innerText;
                summarizeButton.innerText = 'Summarizing...';
                const summary = await callGemini(`Summarize this email in 3 key bullet points:\n\n${emailBody}`);
                alert(`AI Summary:\n\n${summary}`);
                summarizeButton.innerText = '✨ Summarize';
            } else {
                alert("Could not find the email content. All selectors failed.");
            }
        });

        // Add our button to the toolbar
        bottomBar.prepend(summarizeButton);
    }
}

// Run the function periodically to add buttons to newly opened emails
setInterval(addAiButtons, 1000);