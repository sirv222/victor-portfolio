
document.addEventListener("DOMContentLoaded", () => {
    const loader = document.getElementById("page-loader");

    if (!loader) return;

    const hideLoader = () => {
        loader.classList.add("hidden");

        // Remove from the DOM after fade-out
        setTimeout(() => {
            loader.remove();
        }, 700);
    };

    // Handle normal page loading
    if (document.readyState === "complete") {
        hideLoader();
    } else {
        window.addEventListener("load", hideLoader, {
            once: true
        });
    }

    // Handle browser back/forward navigation
    window.addEventListener("pageshow", (event) => {
        if (event.persisted) {
            hideLoader();
        }
    });
});
