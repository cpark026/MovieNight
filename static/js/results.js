// ===== DOM REFERENCES =====
const resultsDiv = document.getElementById("results");

// ===== ADD TO WATCHLIST =====
async function addToWatchlistTMDB(item) {
    try {
        const modal = document.createElement("div");
        modal.id = "ratingModal";
        Object.assign(modal.style, {
            position: "fixed",
            top: "0",
            left: "0",
            width: "100%",
            height: "100%",
            backgroundColor: "rgba(0,0,0,0.7)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            zIndex: "1000"
        });

        const content = document.createElement("div");
        Object.assign(content.style, {
            backgroundColor: "#fff",
            padding: "20px",
            borderRadius: "10px",
            width: "400px",
            maxHeight: "80%",
            overflowY: "auto",
            textAlign: "center"
        });

        const title = document.createElement("h2");
        title.textContent = item.title || item.name;

        const poster = document.createElement("img");
        poster.src = item.poster_path 
            ? "https://image.tmdb.org/t/p/w500" + item.poster_path
            : "../static/placeholder.png";
        poster.style.cssText = "width: 200px; margin: 10px 0;";

        const label = document.createElement("label");
        label.textContent = "Rate this movie (1-10): ";

        const input = document.createElement("input");
        input.type = "number";
        input.min = "1";
        input.max = "10";
        input.value = "5";
        input.style.cssText = "width: 60px; margin-left: 10px;";

        const submitBtn = document.createElement("button");
        submitBtn.textContent = "Add & Rate";
        submitBtn.style.marginTop = "15px";

        submitBtn.onclick = async () => {
            const rating = parseInt(input.value);
            if (isNaN(rating) || rating < 1 || rating > 10) {
                alert("Please enter a valid rating from 1 to 10.");
                return;
            }

            item.userRating = rating;

            try {
                const response = await fetch("/addShow", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(item)
                });

                if (response.ok) {
                    alert(`${item.title} has been added to your watchlist with rating ${rating}!`);
                    modal.remove();
                    window.location.reload();
                } else {
                    alert("Failed to add to watchlist.");
                }
            } catch (err) {
                console.error(err);
                alert("Error adding to watchlist.");
            }
        };

        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };

        content.appendChild(title);
        content.appendChild(poster);
        content.appendChild(label);
        content.appendChild(input);
        content.appendChild(document.createElement("br"));
        content.appendChild(submitBtn);
        modal.appendChild(content);
        document.body.appendChild(modal);

    } catch (error) {
        console.error("Error opening rating modal:", error);
        alert("Failed to add to watchlist. Please try again.");
    }
}

// ===== FETCH EXISTING WATCHLIST IDS =====
async function fetchWatchlistIDs() {
    try {
        const response = await fetch("/getWatchlistIDs");
        const shows = await response.json();
        console.log(shows.map(show => show.mediaID))
        return shows.map(show => show.mediaID);
    } catch (error) {
        console.error("Error fetching watchlist:", error);
        return [];
    }
}

// ===== FETCH TMDB RESULTS AND DISPLAY =====
async function fetchAndDisplayTMDBResults() {
    const params = new URLSearchParams(window.location.search);
    const query = params.get("query") || params.get("showName") || params.get("name");

    if (!query) {
        resultsDiv.innerHTML = "<p>No search query provided.</p>";
        return;
    }

    try {
        // Fetch in parallel
        const [response, watchlistIds] = await Promise.all([
            fetch(`/getResults?name=${encodeURIComponent(query)}`),
            fetchWatchlistIDs()
        ]);

        const data = await response.json();
        
        if (!data || data.length === 0) {
            resultsDiv.innerHTML = "<p>No results found.</p>";
            return;
        }

        // Convert to Set for O(1) lookup
        const watchlistSet = new Set(watchlistIds);
        const fragment = document.createDocumentFragment();
        const title = item => item.title || item.name;

        data.forEach(item => {
            const div = document.createElement("div");
            div.className = "result";

            const h2 = document.createElement("h2");
            h2.textContent = title(item);

            const img = document.createElement("img");
            img.src = item.poster || (item.poster_path ? "https://image.tmdb.org/t/p/w500" + item.poster_path : "../static/images/placeholder.png");
            img.alt = `${title(item)} Poster`;

            const btn = document.createElement("button");
            const exists = watchlistSet.has(item.id);
            btn.textContent = exists ? "Already Rated" : "Rate Movie";
            btn.disabled = exists;
            if (!exists) btn.onclick = () => addToWatchlistTMDB(item);

            div.appendChild(h2);
            div.appendChild(img);
            div.appendChild(btn);
            fragment.appendChild(div);
        });

        resultsDiv.innerHTML = "";
        resultsDiv.appendChild(fragment);
    } catch (err) {
        console.error(err);
        resultsDiv.innerHTML = `<p>Error: ${err.message}</p>`;
    }
}

// ===== INIT =====
document.addEventListener("DOMContentLoaded", fetchAndDisplayTMDBResults);
