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
            
            // Load cached recommendations first (instant display)
            const cachedRecs = sessionStorage.getItem('cachedRecommendations');
            if (cachedRecs) {
                try {
                    const cached = JSON.parse(cachedRecs);
                    console.log('[INDEX] Using cached recommendations from login');
                    displayCachedRecommendations(cached);
                    // Clear from sessionStorage after use
                    sessionStorage.removeItem('cachedRecommendations');
                    // Fetch fresh recommendations in background (skipRebuild=true to preserve cache display)
                    fetchAllRecommendations(true);
                } catch (e) {
                    console.error('Error parsing cached recommendations:', e);
                    fetchAllRecommendations(false);
                }
            } else {
                // No cache, fetch recommendations normally
                fetchAllRecommendations(false);
            }
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
async function fetchAllRecommendations(skipRebuild = false) {
    const fetchStartTime = performance.now();
    
    // Only rebuild DOM if not already showing cached recommendations
    if (!skipRebuild) {
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
    }

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

// ===== DISPLAY CACHED RECOMMENDATIONS (instant load on login) =====
function displayCachedRecommendations(cachedData) {
    console.log('[CACHE] Displaying cached recommendations');
    
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
    
    // Display cached recommendations
    if (cachedData.general?.length) {
        displayRecommendationsSection(cachedData.general, "full-recs-container");
    } else {
        document.getElementById("full-recs-container").innerHTML = "<p>No personalized recommendations available.</p>";
    }
    
    if (cachedData.last_added?.length) {
        displayRecommendationsSection(cachedData.last_added, "last-recs-container");
    } else {
        document.getElementById("last-recs-container").innerHTML = "<p>No last-added recommendations available.</p>";
    }
    
    if (cachedData.genre_based?.length) {
        displayRecommendationsSection(cachedData.genre_based, "genre-recs-container");
    } else {
        document.getElementById("genre-recs-container").innerHTML = "<p>No genre-based recommendations available.</p>";
    }
    
    console.log('[CACHE] Cached recommendations displayed successfully');
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

        // Wrapper for title + thumbs down
        const titleWrapper = document.createElement("div");
        titleWrapper.style.display = "flex";
        titleWrapper.style.alignItems = "center";
        titleWrapper.style.justifyContent = "center";
        titleWrapper.style.width = "100%";

        // Movie title
        const title = document.createElement("h3");
        title.textContent = `#${idx + 1} ${movie.title || "Untitled"}`;
        title.style.margin = 0; 
        titleWrapper.appendChild(title);

        // Thumbs-down icon
        const thumbsDown = document.createElement("span");
        thumbsDown.textContent = "👎"; 
        thumbsDown.style.cursor = "pointer";
        thumbsDown.title = "Dislike";
        thumbsDown.style.marginTop = "4px";
        thumbsDown.style.marginLeft = "5px";
        titleWrapper.appendChild(thumbsDown);
        thumbsDown.addEventListener("click", () => {
    // Hide original card content
    card.innerHTML = "";

    // Create confirmation card
    const confirmCard = document.createElement("div");
    confirmCard.className = "confirmation-card";
    confirmCard.style.border = "1px solid #ccc";
    confirmCard.style.padding = "10px";
    confirmCard.style.borderRadius = "6px";
    confirmCard.style.textAlign = "center";
    confirmCard.style.backgroundColor = "#f9f9f9";

    const message = document.createElement("p");
    message.textContent = "Are you sure you want to dislike this movie?";
    confirmCard.appendChild(message);

    const buttonsWrapper = document.createElement("div");
    buttonsWrapper.style.marginTop = "10px";
    buttonsWrapper.style.display = "flex";
    buttonsWrapper.style.justifyContent = "center";
    buttonsWrapper.style.gap = "10px";

    const cancelBtn = document.createElement("button");
    cancelBtn.textContent = "Cancel";
    cancelBtn.style.padding = "5px 10px";
    cancelBtn.style.cursor = "pointer";

    const confirmBtn = document.createElement("button");
    confirmBtn.textContent = "Confirm";
    confirmBtn.style.padding = "5px 10px";
    confirmBtn.style.cursor = "pointer";

    buttonsWrapper.appendChild(cancelBtn);
    buttonsWrapper.appendChild(confirmBtn);
    confirmCard.appendChild(buttonsWrapper);

    card.appendChild(confirmCard);

    // Cancel restores original card
cancelBtn.addEventListener("click", () => {
    card.innerHTML = "";
    card.appendChild(titleWrapper);

    // GENRES
    if (movie.genres) {
        const genres = document.createElement("p");
        genres.className = "genres";
        genres.textContent = Array.isArray(movie.genres)
            ? `Genres: ${movie.genres.join(", ")}`
            : `Genres: ${String(movie.genres).replace(/\|/g, ", ")}`;
        card.appendChild(genres);
    }

    // OVERVIEW
    if (movie.overview) {
        const overview = document.createElement("p");
        overview.className = "overview";
        overview.textContent = movie.overview;
        card.appendChild(overview);
    }

    // SCORES
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

    // CAST OVERLAP
    if (movie.cast_overlap?.length) {
        const overlap = document.createElement("p");
        overlap.className = "cast-overlap";
        overlap.textContent = `Cast Overlap: ${movie.cast_overlap.join(", ")}`;
        card.appendChild(overlap);
    }

    // REFERENCE MOVIE
    if (movie.reference_movie) {
        const ref = document.createElement("p");
        ref.className = "reference";
        ref.textContent = `Based on: ${movie.reference_movie}`;
        card.appendChild(ref);
    }
});

        confirmBtn.addEventListener("click", async () => {
            try {
                // Get user ID from session
                const userRes = await fetch("/api/check-auth", {
                    credentials: 'include'
                });
                const userData = await userRes.json();
                
                if (!userData.authenticated) {
                    console.error("User not authenticated");
                    return;
                }

                const userId = userData.user_id;

                // Send dislike to backend
                const response = await fetch('/api/dislike', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-User-ID': userId
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        movie_id: movie.id || null,
                        movie_title: movie.title,
                        recommendation_set_id: movie.recommendation_set_id || null,
                        predicted_score: movie.scores?.hybrid_score || movie.hybrid_score || 0.0,
                        reason: "not_interested",
                        feedback_text: "",
                        genres: Array.isArray(movie.genres) ? movie.genres : (movie.genres ? movie.genres.split("|") : []),
                        cast: movie.cast || []
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    console.log('[FEEDBACK] Dislike recorded:', data.dislike_id);
                    
                    // Show confirmation message
                    card.innerHTML = "";
                    const confirmation = document.createElement("div");
                    confirmation.textContent = "✓ Dislike recorded. We'll improve recommendations!";
                    confirmation.style.color = "#28a745";
                    confirmation.style.textAlign = "center";
                    confirmation.style.padding = "15px";
                    confirmation.style.fontSize = "14px";
                    confirmation.style.fontWeight = "bold";
                    card.appendChild(confirmation);
                    
                    // Fade out card after 2 seconds, then fetch new recommendations
                    setTimeout(() => {
                        card.style.opacity = "0";
                        card.style.transition = "opacity 0.5s ease-out";
                        setTimeout(() => {
                            card.style.display = "none";
                            // Fetch new recommendations to replace the disliked one
                            console.log('[FEEDBACK] Fetching fresh recommendations after dislike...');
                            fetchAllRecommendations();
                        }, 500);
                    }, 2000);
                } else {
                    console.error('[FEEDBACK] Error recording dislike:', data.error);
                    card.innerHTML = "";
                    const errorDiv = document.createElement("div");
                    errorDiv.textContent = "Error recording dislike. Please try again.";
                    errorDiv.style.color = "#dc3545";
                    errorDiv.style.textAlign = "center";
                    errorDiv.style.padding = "15px";
                    card.appendChild(errorDiv);
                }
            } catch (err) {
                console.error('[FEEDBACK] Network error:', err);
                card.innerHTML = "";
                const errorDiv = document.createElement("div");
                errorDiv.textContent = "Network error. Please try again.";
                errorDiv.style.color = "#dc3545";
                errorDiv.style.textAlign = "center";
                errorDiv.style.padding = "15px";
                card.appendChild(errorDiv);
            }
        });
});


        // Append wrapper to card
        card.appendChild(titleWrapper);
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
