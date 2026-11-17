
(() => {
    const loader = document.getElementById("page-loader");

    if (!loader) return;

    function hideLoader() {
        loader.classList.add("hidden");

        setTimeout(() => loader.remove(), 750);
    }

    if (document.readyState === "complete") {
        hideLoader();
    } else {
        window.addEventListener("load", hideLoader, {
            once: true
        });
    }
})();
