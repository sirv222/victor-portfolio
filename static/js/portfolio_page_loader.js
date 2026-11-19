(() => {
    const loader = document.getElementById("page-loader");

    if (!loader) return;

    let isHidden = false;

    function hideLoader() {
        if (isHidden) return;

        isHidden = true;
        loader.classList.add("hidden");

        setTimeout(() => {
            loader.remove();
        }, 750);
    }

    // Hide loader after the page finishes loading
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

    // Show loader immediately before navigating to another page
    document.addEventListener("click", (event) => {
        const link = event.target.closest("a");

        if (!link) return;

        // Ignore external links
        if (link.origin !== window.location.origin) return;

        // Ignore links opening in another tab
        if (link.target === "_blank") return;

        // Ignore downloads
        if (link.hasAttribute("download")) return;

        // Ignore email links
        if (link.protocol === "mailto:") return;

        // Ignore telephone links
        if (link.protocol === "tel:") return;

        // Ignore clicks inside the contact form
        if (event.target.closest("#contact-form")) return;

        // Ignore links to the current page, including query strings and fragments
        const currentURL = new URL(window.location.href);
        const targetURL = new URL(link.href);

        if (
            currentURL.origin === targetURL.origin &&
            currentURL.pathname === targetURL.pathname
        ) return;

        // Ignore modified clicks
        if (
            event.ctrlKey ||
            event.shiftKey ||
            event.altKey ||
            event.metaKey
        ) return;

        // Ignore same-page navigation
        if (link.href === window.location.href) return;

        // Show loader before navigation
        isHidden = false;
        loader.classList.remove("hidden");
    });

})();