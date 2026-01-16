document.addEventListener("DOMContentLoaded", function () {
  AOS.init({
    duration: 1000,
  });

  const sendButton = document.getElementById("send-button");
  const verifyButton = document.getElementById("verify-button");
  const submitButton = document.getElementById("submit-button");
  const errorMessage = document.getElementById("error-message");

  let sentOtp = "";

  sendButton.addEventListener("click", function () {
    const emailInput = document.getElementById("email");
    const email = emailInput.value;

    if (validateEmail(email)) {
      fetch("http://localhost:3000/send-otp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email: email }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            sentOtp = data.otp; // Save the sent OTP
            sendButton.textContent = "Sent";
            sendButton.style.backgroundColor = "#28a745"; // Green color
            sendButton.style.color = "#fff"; // White text
            sendButton.disabled = true;
            sendButton.style.cursor = "not-allowed";
            verifyButton.disabled = false;
            verifyButton.style.cursor = "pointer";
          } else {
            alert("Failed to send OTP. Please try again.");
          }
        })
        .catch((error) => {
          console.error("Error:", error);
        });
    } else {
      alert("Please enter a valid email address.");
    }
  });

  verifyButton.addEventListener("click", function () {
    const otpInput = document.getElementById("otp");
    const otp = otpInput.value;

    fetch("http://localhost:3000/verify-otp", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: document.getElementById("email").value,
        otp: otp,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          verifyButton.textContent = "Verified";
          verifyButton.style.backgroundColor = "#28a745"; // Green color
          verifyButton.style.color = "#fff"; // White text
          verifyButton.disabled = true;
          verifyButton.style.cursor = "not-allowed";
          submitButton.disabled = false;
          submitButton.classList.remove("disabled");
          submitButton.style.cursor = "pointer";
          errorMessage.textContent = ""; // Clear error message
        } else {
          errorMessage.textContent = "Invalid OTP. Please try again.";
          verifyButton.style.backgroundColor = "#dc3545"; // Red color
          verifyButton.style.color = "#fff"; // White text
        }
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  });

  function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
  }
});
