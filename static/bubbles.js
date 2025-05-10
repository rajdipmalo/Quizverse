
function createBubbles() {
    const bubbleBg = document.getElementById('bubble-bg');
    const bubbleCount = 25;
            
            // Clear any existing bubbles first
    bubbleBg.innerHTML = '';
            
    for (let i = 0; i < bubbleCount; i++) {
        const bubble = document.createElement('div');
        bubble.classList.add('bubble');
                
                // Random size between 30px and 150px
        const size = Math.random() * 120 + 30;
        bubble.style.width = `${size}px`;
        bubble.style.height = `${size}px`;
        
        // Random position
        bubble.style.left = `${Math.random() * 100}%`;
        
        // Random animation duration between 8s and 20s
        const duration = Math.random() * 12 + 8;
        bubble.style.animation = `float ${duration}s infinite ease-in`;
        
        // Random delay
        bubble.style.animationDelay = `${Math.random() * 3}s`;
        
        // Random opacity (slightly higher for darker effect)
        bubble.style.opacity = Math.random() * 0.4 + 0.5;
        
        // Darker blue shades
        const hue = 220 + Math.random() * 20;          // Deep blue to royal blue (220–240)
        const saturation = 60 + Math.random() * 20;     // 60–80% saturation
        const lightness = 30 + Math.random() * 10;      // 30–40% lightness for dark color
        const alpha = Math.random() * 0.3 + 0.6;        // Stronger opacity for visibility
        
        bubble.style.backgroundColor = `hsla(${hue}, ${saturation}%, ${lightness}%, ${alpha})`;
        bubble.style.filter = 'blur(5px)';
        
        bubbleBg.appendChild(bubble);
    }
}
        
document.addEventListener('DOMContentLoaded', function() {
    createBubbles();
});
