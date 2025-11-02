Operations Index
================

.. raw:: html

  <nav class="under-title-tabs">
    See also:
    <a href="facts.html">Facts Index</a>
    <a href="connectors.html">Connectors Index</a>
  </nav>

Operations are used to describe changes to make to systems in the inventory. Use them to define state and pyinfra will make any necessary changes to reach that state. All operations accept a set of :doc:`global arguments <arguments>` and are grouped as Python modules.

**Want a new operation?** Check out :doc:`the writing operations guide <./api/operations>`.

.. raw:: html

        <div class="container my-4">
          <!-- Dropdown Filter -->
          <div class="mb-4">
            <label for="tag-dropdown" class="form-label">Filter by Tag:</label>
            <select class="form-select" id="tag-dropdown">
	      <option value="All">All</option>
{% for tag in tags %}
              <option value="{{ tag.title_case }}">{{ tag.title_case }}</option>
{% endfor %}
            </select>
          </div>

          <!-- Cards Grid -->
          <div class="row" id="card-container">
{% for plugin in operation_plugins %}
            <div class="col-md-4 mb-4 card-item">
              <div class="card h-100">
                <div class="card-body">
                  <h5 class="card-title">
                    <a href="./operations/{{ plugin.name }}.html">
                      {{ plugin.name }}
                    </a>
                  </h5>
                  <p class="card-text">{{ plugin.description }}</p>
{% for tag in plugin.tags %}
                  <span class="badge bg-secondary">{{ tag.title_case }}</span>
{% endfor %}
                </div>
              </div>
            </div>
{% endfor %}
          </div>
        </div>
        <script>
          document.getElementById('tag-dropdown').addEventListener('change', function () {
            const selectedTag = this.value;
            const cards = document.querySelectorAll('.card-item');

            cards.forEach(card => {
              const tags = Array.from(card.querySelectorAll('.badge')).map(badge => badge.textContent.trim());

              if (selectedTag === 'All' || tags.includes(selectedTag)) {
                card.style.display = 'block';
              } else {
                card.style.display = 'none';
              }
            });
          });
        </script>

.. toctree::
   :maxdepth: 2
   :glob:
   :hidden:

   operations/*
