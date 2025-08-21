// This function runs when the popup window is opened
document.addEventListener('DOMContentLoaded', () => {
  const apiKeyInput = document.getElementById('apiKey');
  const saveButton = document.getElementById('save');

  // Load and display any key that's already saved
  chrome.storage.sync.get(['geminiApiKey'], (result) => {
    if (result.geminiApiKey) {
      apiKeyInput.value = result.geminiApiKey;
    }
  });

  // Add a click listener to the save button
  saveButton.addEventListener('click', () => {
    const apiKey = apiKeyInput.value;
    if (apiKey) {
      // Save the key using the Chrome storage API
      chrome.storage.sync.set({ 'geminiApiKey': apiKey }, () => {
        saveButton.textContent = 'Saved!';
        // Change the text back after a moment
        setTimeout(() => {
          saveButton.textContent = 'Save';
        }, 1500);
      });
    }
  });
});