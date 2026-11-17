  <script>
    const SUPABASE_URL = "https://pzaavnfswisvosgdfbgl.supabase.co";
    const SUPABASE_ANON_KEY = "sb_publishable_PASTE_YOUR_KEY_HERE";

    async function loadProducts() {
      const statusEl = document.getElementById("status");
      const gridEl = document.getElementById("product-grid");

      try {
        const res = await fetch(
          `${SUPABASE_URL}/rest/v1/marketplace_products?select=title,seller_contact,price_value,image_url&order=created_at.desc`,
          {
            headers: {
              apikey: SUPABASE_ANON_KEY
            }
          }
        );

        if (!res.ok) {
          const errText = await res.text();
          throw new Error(`HTTP ${res.status}: ${errText}`);
        }

        const products = await res.json();

        if (!products.length) {
          statusEl.textContent = "New software drops arriving shortly. Check back soon!";
          return;
        }

        statusEl.style.display = "none";

        products.forEach((item) => {
          const fallbackImg = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800";
          const card = document.createElement("article");
          card.className = "card";
          card.innerHTML = `
            <img src="${item.image_url || fallbackImg}" alt="${item.title}" loading="lazy" />
            <div class="card-body">
              <span class="badge">Instant Digital Access</span>
              <h2>${item.title}</h2>
              <div class="price">$${Number(item.price_value).toFixed(2)} <span>USD</span></div>
              <a class="btn" href="${item.seller_contact}" target="_blank" rel="nofollow sponsored noopener">Get Instant Access →</a>
            </div>
          `;
          gridEl.appendChild(card);
        });
      } catch (err) {
        statusEl.textContent = `Error: ${err.message}`;
        console.error(err);
      }
    }

    loadProducts();
  </script>
