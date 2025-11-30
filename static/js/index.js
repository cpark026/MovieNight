// ===== CACHE MANAGEMENT =====
let cachedWatchlist = null;

// ===== DOM REFERENCES =====
const mainElement = document.getElementById("main-content");

// ===== INITIALIZATION =====
document.addEventListener("DOMContentLoaded", () => {
    checkAuthAndDisplayUsername();

    const button = document.getElementById("searchButton");
    if (button) {
        button.addEventListener("click", () => {
            const inputValue = document.getElementById("searchInput").value;
            redirectToResults({ showName: inputValue });
        });
    }
});

// ===== AUTHENTICATION =====
async function checkAuthAndDisplayUsername() {
    try {
        const res = await fetch("/api/check-auth", {
            credentials: 'include'  // Include cookies for session
        });
        const data = await res.json();

        if (data.authenticated && data.username) {
            const usernameDisplay = document.getElementById("usernameDisplay");
            if (usernameDisplay) {
                usernameDisplay.textContent = `Welcome, ${data.username}`;
            }
            fetchAllRecommendations();
        } else {
            window.location.href = "/";
        }
    } catch (err) {
        console.error("Error checking auth:", err);
        window.location.href = "/";
    }
}

async function logout() {
    try {
        const res = await fetch("/api/logout", {
            method: "POST",
            credentials: 'include'
        });
        if (res.ok) {
            window.location.href = "/";
        } else {
            alert("Logout failed");
        }
    } catch (err) {
        console.error("Logout error:", err);
        alert("An error occurred during logout");
    }
}

// ===== FETCH RECOMMENDATIONS =====
async function fetchAllRecommendations() {
    const fetchStartTime = performance.now();
    mainElement.innerHTML = `
        <section id="full-recs-section">
            <h2>Personalized Recommendations</h2>
            <div id="full-recs-container"><p>Loading…</p></div>
        </section>
        <section id="last-recs-section" style="margin-top: 2rem;">
            <h2 id="last-recs-title">Because You Last Added</h2>
            <div id="last-recs-container"><p>Loading…</p></div>
        </section>
        <section id="genre-recs-section" style="margin-top: 2rem;">
            <h2 id="genre-recs-title">Based on your most watched genre</h2>
            <div id="genre-recs-container"><p>Loading…</p></div>
        </section>
    `;

    try {
        const [fullData, lastData, lastMovieData, genreData, mostCommonGenreData] = await Promise.all([
            fetch("/getRecommendations", { credentials: 'include' }).then(r => r.ok ? r.json() : null),
            fetch("/getLastWatchedRecommendations", { credentials: 'include' }).then(r => r.ok ? r.json() : null),
            fetch("/getLastAddedMovie", { credentials: 'include' }).then(r => r.ok ? r.json() : null),
            fetch("/getMostCommonGenreRecommendations", { credentials: 'include' }).then(r => r.ok ? r.json() : null),
            fetch("/getMostCommonGenre", { credentials: 'include' }).then(r => r.ok ? r.json() : null)
        ]);
        
        const fetchEndTime = performance.now();
        const fetchDuration = ((fetchEndTime - fetchStartTime) / 1000).toFixed(2);
        console.log(`[TIMER] All API calls completed in ${fetchDuration}s`);

        // Personalized Recommendations
        if (fullData?.recommendations?.length) {
            displayRecommendationsSection(fullData.recommendations, "full-recs-container");
        } else {
            document.getElementById("full-recs-container").innerHTML = "<p>No personalized recommendations available.</p>";
        }

        // Last-Added Recommendations
        if (lastData?.recommendations?.length) {
            displayRecommendationsSection(lastData.recommendations, "last-recs-container");
        } else {
            document.getElementById("last-recs-container").innerHTML = "<p>No last-added recommendations available.</p>";
        }
        if (lastMovieData?.title) {
            const titleEl = document.getElementById("last-recs-title");
            if (titleEl) titleEl.textContent = `Because You Last Added: ${lastMovieData.title}`;
        }

        // Genre-Based Recommendations
        if (genreData?.recommendations?.length) {
            displayRecommendationsSection(genreData.recommendations, "genre-recs-container");
        } else {
            document.getElementById("genre-recs-container").innerHTML = "<p>No genre-based recommendations available.</p>";
        }
        if (mostCommonGenreData?.most_common_genre) {
            const titleEl = document.getElementById("genre-recs-title");
            if (titleEl) titleEl.textContent = `Based on your most watched genre: ${mostCommonGenreData.most_common_genre}`;
        }

    } catch (err) {
        console.error("Error fetching recommendations:", err);
        mainElement.innerHTML = "<p>Failed to load recommendations.</p>";
    }
}

// ===== DISPLAY SECTION (reusable) =====
function displayRecommendationsSection(recommendations, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!recommendations.length) {
        container.innerHTML = "<p>No recommendations available.</p>";
        return;
    }

    const grid = document.createElement("div");
    grid.className = "recommendations-grid";

    recommendations.forEach((movie, idx) => {
        const card = document.createElement("div");
        card.className = "recommendation-card";

        const title = document.createElement("h3");
        title.textContent = `#${idx + 1} ${movie.title || "Untitled"}`;
        card.appendChild(title);

        console.log(movie)

        if (movie.genres) {
            const genres = document.createElement("p");
            genres.className = "genres";
            genres.textContent = Array.isArray(movie.genres) ? `Genres: ${movie.genres.join(", ")}` : `Genres: ${String(movie.genres).replace(/\|/g, ", ")}`;
            card.appendChild(genres);
        }

        if (movie.overview) {
            const overview = document.createElement("p");
            overview.className = "overview";
            overview.textContent = movie.overview;
            card.appendChild(overview);
        }

        const genreSim = movie.scores?.genre_sim ?? movie.genre_sim ?? 0;
        const castSim = movie.scores?.cast_sim ?? movie.cast_sim ?? 0;
        const franchiseSim = movie.scores?.franchise_sim ?? movie.franchise_sim ?? 0;
        const hybridScore = movie.scores?.hybrid_score ?? movie.hybrid_score ?? 0;

        if (genreSim || castSim || franchiseSim || hybridScore) {
            const scores = document.createElement("div");
            scores.className = "scores";
            scores.innerHTML = `
                <p><strong>Scores:</strong></p>
                <p>Genre Match: ${(Number(genreSim) * 100).toFixed(1)}%</p>
                <p>Cast Match: ${(Number(castSim) * 100).toFixed(1)}%</p>
                <p>Franchise Match: ${(Number(franchiseSim) * 100).toFixed(1)}%</p>
                <p><strong>Overall Score: ${(Number(hybridScore) * 100).toFixed(1)}%</strong></p>
            `;
            card.appendChild(scores);
        }

        if (movie.cast_overlap?.length) {
            const overlap = document.createElement("p");
            overlap.className = "cast-overlap";
            overlap.textContent = `Cast Overlap: ${movie.cast_overlap.join(", ")}`;
            card.appendChild(overlap);
        }

        if (movie.reference_movie) {
            const ref = document.createElement("p");
            ref.className = "reference";
            ref.textContent = `Based on: ${movie.reference_movie}`;
            card.appendChild(ref);
        }

        grid.appendChild(card);
    });

    container.innerHTML = "";
    container.appendChild(grid);
}

// ===== REDIRECT TO RESULTS PAGE =====
function redirectToResults(input) {
    const showName = encodeURIComponent(input.showName || "");
    window.location.href = `results?name=${showName}`;
}
