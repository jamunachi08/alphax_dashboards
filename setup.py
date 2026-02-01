from setuptools import setup, find_packages

# Frappe uses setup.py metadata for packaging
setup(
    name="alphax_dashboards",
    version="0.1.0",
    description="AlphaX Dashboards - CRM, Finance and HRMS web dashboards for Frappe/ERPNext",
    author="AlphaX / Neotech",
    author_email="",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
)
