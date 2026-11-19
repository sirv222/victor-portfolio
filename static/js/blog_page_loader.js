(() => {
    const loader = document.getElementById("page-loader");

    if (!loader) return;

    function hideLoader() {
        loader.classList.add("hidden");
    }

    function showLoader() {
        loader.classList.remove("hidden");
    }

    // Hide loader after initial page load
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

    // Show loader before navigating to another page
    document.addEventListener("click", (event) => {
        const link = event.target.closest("a");

        if (!link) return;

        // Ignore contact form
        if (event.target.closest("#contact-form")) return;

        // Ignore external links
        if (link.origin !== window.location.origin) return;

        // Ignore email and telephone links
        if (["mailto:", "tel:"].includes(link.protocol)) return;

        // Ignore new tabs
        if (link.target === "_blank") return;

        // Ignore downloads
        if (link.hasAttribute("download")) return;

        // Ignore modified clicks
        if (
            event.ctrlKey ||
            event.shiftKey ||
            event.altKey ||
            event.metaKey
        ) return;

        // Ignore links to the same page
        const currentURL = new URL(window.location.href);
        const targetURL = new URL(link.href);

        if (currentURL.pathname === targetURL.pathname) return;

        // Show loader
        showLoader();
    });

})();