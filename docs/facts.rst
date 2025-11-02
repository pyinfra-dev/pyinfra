Facts Index
===========

.. raw:: html

  <nav class="under-title-tabs">
    See also:
    <a href="operations.html">Operations Index</a>
    <a href="connectors.html">Connectors Index</a>
  </nav>

pyinfra uses **facts** to determine the existing state of a remote server. Operations use this information to generate commands which alter the state. Facts are read-only and are populated at the beginning of the deploy.

Facts can be executed/tested via the command line:

.. code:: sh

    # Example how to get multiple facts from a server myhost.com
    pyinfra myhost.com fact server.Date server.Hostname ...

If you want to pass an argument to a fact, pass it with ``key=value``. For example:

.. code:: sh

    # See if the package 'openssh-server' is installed servers myhost.com and myhost2.com
    pyinfra myhost.com,myhost2.com fact deb.DebPackage name=openssh-server

Multiple facts with arguments may be called like so:

.. code:: sh

    pyinfra @local fact files.File path=setup.py files.File path=anotherfile.txt

You can leverage facts within :doc:`operations <using-operations>` like this:

.. code:: py

    from pyinfra import host
    from pyinfra.facts.server import LinuxName

    if host.get_fact(LinuxName) == 'Ubuntu':
        apt.packages(...)

**Want a new fact?** Check out :doc:`the writing facts guide <./api/operations>`.

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
{% for plugin in fact_plugins %}
            <div class="col-md-4 mb-4 card-item">
              <div class="card h-100">
                <div class="card-body">
                  <h5 class="card-title">
                    <a href="./facts/{{ plugin.name }}.html">
                      {{ plugin.name }}
                    </a>
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

   facts/*
