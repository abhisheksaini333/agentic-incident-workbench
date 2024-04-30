SERVICES = {
    "heap-api": "memory_pressure",
    "busy-api": "cpu_saturation",
    "release-api": "bad_release",
    "catalog-api": "dependency_outage",
    "storage-api": "disk_pressure",
    "queue-api": "queue_backlog",
}


def seed_demo(auth, tools, password):
    created = 0
    for tenant in ["acme", "beta"]:
        for role in ["viewer", "operator", "approver", "admin"]:
            subject = tenant + "." + role
            if auth.store.account(subject) is None:
                auth.create_account(tenant, subject, password, [role])
                created += 1
        for service, fault in SERVICES.items():
            observed = tools.provision(tenant, service)
            if observed["generation"] == 1:
                tools.inject(tenant, service, [fault])
    return {"accounts_created": created, "services_per_tenant": len(SERVICES)}
