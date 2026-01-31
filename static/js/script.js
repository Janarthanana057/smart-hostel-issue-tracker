// Global Slider Variables
let slideIdx = 0;
const totalSlides = 4;

// --- 1. Image Slider Logic (Round Robin) ---
function moveSlider() {
    const slider = document.getElementById('imgSlider');
    
    // 1. Guard Clause: If the element is NOT on this page, stop here
    if (!slider) {
        return; 
    }

    // 2. The code only reaches this part if 'imgSlider' actually exists
    slider.style.transform = `translateX(-${slideIdx * 25}%)`;
    console.log("Moving to slide: " + slideIdx);
}

function plusSlides(n) {
    slideIdx += n;
    
    // Round Robin Logic: If at the end, go to the start. If at the start, go to the end.
    if (slideIdx >= totalSlides) { slideIdx = 0; }
    if (slideIdx < 0) { slideIdx = totalSlides - 1; }
    
    moveSlider();
}

// --- 2. Captcha Security Logic ---
function generateCaptcha() {
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz23456789";
    let code = "";
    for (let i = 0; i < 5; i++) {
        code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    const captchaElement = document.getElementById("captcha-code");
    if (captchaElement) {
        // Writes the code into the yellow box
        captchaElement.innerText = code;
    }
}

function validateCaptcha() {
    const generated = document.getElementById("captcha-code").innerText;
    const userInp = document.getElementById("captcha-input").value;
    
    // Checks if the typed code matches the generated code
    if (userInp != generated) {
        alert("Invalid Security Code! Please try again.");
        generateCaptcha(); // Reset captcha on fail
        return false; 
    }
    return true; 
}

// --- 3. Run Setup & Automatic Features ---
document.addEventListener('DOMContentLoaded', () => {
    // A. Generate the initial Captcha
    generateCaptcha();

    // B. Start Automatic Image Rotation (Every 5 seconds)
    setInterval(() => {
        plusSlides(1);
    }, 2000);

    // C. Handle Likes/Reactions on Public Issues
    const reactionButtons = document.querySelectorAll('.reaction-btn');
    reactionButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            this.classList.toggle('active');
            let countSpan = this.querySelector('.count');
            let currentCount = parseInt(countSpan.innerText);
            
            if(this.classList.contains('active')) {
                countSpan.innerText = currentCount + 1;
                this.style.color = '#3498db';
            } else {
                countSpan.innerText = currentCount - 1;
                this.style.color = '#333';
            }
        });
    });

    // D. Auto-dismiss Flash Messages after 3 seconds
    setTimeout(() => {
        const flashes = document.querySelectorAll('.flash-message');
        flashes.forEach(f => f.style.display = 'none');
    }, 3000);
});