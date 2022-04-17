from pyinfra.api import FactBase


class LaunchdStatus(FactBase):
    """
    Returns a dict of name -> status for launchd managed services.
    """

    command = "launchctl list"
    requires_command = "launchctl"

    default = dict

    def process(self, output):
        services = {}

        for line in output:
            bits = line.split()

            if not bits or bits[0] == "PID":
                continue

            name = bits[2]
            status = False

            try:
                int(bits[0])
                status = True
            except ValueError:
                pass

            services[name] = status

        return services
