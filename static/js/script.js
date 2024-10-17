async function postData(url = "", data = {}) { 
  const response = await fetch(url, {
    method: "POST", headers: {
      "Content-Type": "application/json", 
    }, body: JSON.stringify(data),  
  });
  return response.json(); 
}

sendButton.addEventListener("click", async () => {
  const questionInput = document.getElementById("questionInput").value;

  if (questionInput === "") {
    // If input is empty, don't send
    alert("Please enter a message before sending.");
    return; // Exit the function
  }
  // Clear input field after the question is submitted
  document.getElementById("questionInput").value = "";

  // Display the right2 div and hide right1 after the first question
  document.querySelector(".right2").style.display = "block";
  document.querySelector(".right1").style.display = "none";

  // Append the question and the AI's answer dynamically to the right2 div
  const chatContainer = document.querySelector(".right2");

  const questionHtml = `
      <div class="box1 m-auto py-7 flex justify-start w-[40vw] items-center space-x-6">
          <img class="w-9" src="/static/image/user.png" alt="">
          <div>${questionInput}</div>
      </div>
  `;

  const loadingAnswerHtml = `
      <div class="loading-box bg-gray-600 py-7 flex justify-center w-full items-center">
          <div class="box w-[40vw] flex justify-start space-x-6">
              <img class="w-9 h-9" src="/static/image/ai.webp" alt="">
              <div class="flex space-y-4 flex-col">
                  <div>Loading...</div>
              </div>
          </div>
      </div>
  `;

  chatContainer.innerHTML += questionHtml;
  chatContainer.innerHTML += loadingAnswerHtml;

  // Get the answer and replace the loading message
  const result = await postData("/api", {"question": questionInput});
  
  const answerHtml = `
      <div class="box2 bg-gray-600 py-7 flex justify-center w-full items-center">
          <div class="box w-[40vw] flex justify-start space-x-6">
              <img class="w-9 h-9" src="/static/image/ai.webp" alt="">
              <div class="flex space-y-4 flex-col">
                  <div>${result.answer}</div>
              </div>
          </div>
      </div>
  `;

  // Remove the loading element before appending the answer
  const loadingBox = document.querySelector(".loading-box");
  loadingBox.remove(); // Remove the loading div

  // Append the actual answer
  chatContainer.innerHTML += answerHtml;
});
