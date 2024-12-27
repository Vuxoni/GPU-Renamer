import plistlib, subprocess, os, shutil, datetime, requests, stat, zipfile


# Load the config
def load_config(plist_path):
    try:
        with open(plist_path, 'rb') as f:
            return plistlib.load(f)
    except Exception as e:
        # Something broke
        print(f"Error loading your config.plist: {e}")
        return None

# Save the config, let's hope nothing breaks here
def save_config(plist_path, plist_data):
    try:
        with open(plist_path, 'wb') as f:
            plistlib.dump(plist_data, f)
        # Yay, it saved
        print("config.plist saved successfully!")
    except Exception as e:
        # Fuck
        print(f"Error saving your config.plist: {e}")

# Create the backup, just in case
def create_backup(plist_path):
    try:
        backup_path = f"{plist_path}.backup"
        shutil.copy(plist_path, backup_path)
        print(f"Backup created: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"Error creating backup: {e}")
        return None

def change_gpu_name(plist_data, new_name):
    if "DeviceProperties" not in plist_data:
        plist_data["DeviceProperties"] = {}

    if device_key not in plist_data["DeviceProperties"]:
        plist_data["DeviceProperties"][device_key] = {}

    plist_data["DeviceProperties"][device_key]["model"] = new_name
    return plist_data

def add_pci_root(plist_data, pci_root):
    if "DeviceProperties" not in plist_data:
        plist_data["DeviceProperties"] = {}

    if "Add" not in plist_data["DeviceProperties"]:
        plist_data["DeviceProperties"]["Add"] = {}

    # Initialize the PCI Root structure if it does not exist
    if pci_root not in plist_data["DeviceProperties"]["Add"]:
        plist_data["DeviceProperties"]["Add"][pci_root] = {"model": ""}  # Initialize with an empty model

    return plist_data

def download_gfxutil(version='RELEASE'):
    url = "https://api.github.com/repos/acidanthera/gfxutil/releases/latest"
    response = requests.get(url)

    if response.status_code != 200:
        print("Error fetching release data.")
        return

    data = response.json()

    print("Available assets:")
    for asset in data['assets']:
        print(f"- {asset['name']}")

    gfxutil_url = None
    for asset in data['assets']:
        if version in asset['name'] and asset['name'].endswith('.zip'):
            gfxutil_url = asset['browser_download_url']
            break

    if gfxutil_url:
        zip_response = requests.get(gfxutil_url)
        zip_path = 'gfxutil.zip'
        with open(zip_path, 'wb') as f:
            f.write(zip_response.content)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall('.')  

        os.chmod('./gfxutil', 0o755)
        print("gfxutil downloaded and extracted successfully!")

        os.remove(zip_path)
    else:
        print(f"Error: Could not find a suitable gfxutil download for version '{version}'.")

download_gfxutil(version='RELEASE')

def get_pci_root():
    gfxutil_path = './gfxutil'

    if not os.access(gfxutil_path, os.X_OK):
        try:
            st = os.stat(gfxutil_path)
            os.chmod(gfxutil_path, st.st_mode | stat.S_IEXEC)
            print(f"gfxutil was not executable, but it is now.")
        except Exception as e:
            print(f"Failed to make gfxutil executable: {e}")
            return None
    try: 
        result = subprocess.run(["./gfxutil", "-f", "display"], capture_output=True, text=True)
        output = result.stdout.strip()
        pci_roots = []

        for line in output.splitlines():
            if "PciRoot" in line:
                pci_root = line.split("= ")[1].strip()
                pci_roots.append(pci_root)

        if len(pci_roots) > 1:
            print("Multiple device paths found:")
            for i, pci_root in enumerate(pci_roots):
                print(f"{i}: {pci_root}")
            while True:
                try:
                    choice = int(input("Enter the number of the device path to use: "))
                    if 0 <= choice < len(pci_roots):
                        return pci_roots[choice]
                    else:
                        print(f"Please enter a number between 0 and {len(pci_roots)}.")
                except ValueError:
                    print("Invalid input. Please enter a valid number.")
            return pci_roots[choice]

        elif len(pci_roots) == 1:
            return pci_roots[0]

        else:
            print("No device paths found.")
            return None

    except Exception as e:
        print(f"Error running gfxutil: {e}")
        return None

def clean_path(path):
    path = path.strip()
    path = path.replace("\\", "")
    return path

def main():
    print("########################################")
    print("#--------------GPURenamer--------------#")
    print("########################################")
    
    while True:
        print("\nSelect an option:")
        print("1. Auto-detect PCI Root and update GPU name")
        print("2. Manually enter PCI Root and update GPU name")
        print("3. Exit")

        choice = input("Enter your choice (1, 2 or 3): ")

        if choice == '1':
            print("Drag and drop your config.plist file here:")
            plist_path = input().strip()
            plist_path = clean_path(plist_path)

            create_backup(plist_path)

            pci_root = get_pci_root()
            if not pci_root:
                print("Error detecting PCI Root. Please try manually or ensure gfxutil is present.")
                continue
            
            gpu_name = input("Enter the new GPU name:")
            plist_data = load_config(plist_path)
            if plist_data is None:
                print("Failed to load config.plist. Please check the file and try again.")
                continue
            if "DeviceProperties" in plist_data and "Add" in plist_data["DeviceProperties"]:
                if pci_root in plist_data["DeviceProperties"]["Add"] and "model" in plist_data["DeviceProperties"]["Add"][pci_root]:
                    print(f"The PCI Root '{pci_root}' already contains a model entry.")
                    overwrite = input("Do you want to overwrite it? (y/n): ").lower()
                    if overwrite == 'n':
                        print("No changes made to the existing PCI Root entry.")
                        main()
                        return plist_data
            plist_data = add_pci_root(plist_data, pci_root)
            plist_data["DeviceProperties"]["Add"][pci_root]["model"] = gpu_name
            save_config(plist_path, plist_data)
            print(f"Updated {pci_root} with GPU name '{gpu_name}'.")

        elif choice == '2':
            print("Drag and drop your config.plist file here:")
            plist_path = input().strip()
            plist_path = clean_path(plist_path)

            create_backup(plist_path)

            pci_root = input("Enter the PCI Root to add: ")
            gpu_name = input("Enter the GPU name: ")
            plist_data = load_config(plist_path)
            if "DeviceProperties" in plist_data and "Add" in plist_data["DeviceProperties"]:
                if pci_root in plist_data["DeviceProperties"]["Add"] and "model" in plist_data["DeviceProperties"]["Add"][pci_root]:
                    print(f"The PCI Root '{pci_root}' already contains a model entry.")
                    overwrite = input("Do you want to overwrite it? (y/n): ").lower()
                    if overwrite == 'n':
                        print("No changes made to the existing PCI Root entry.")
                        return plist_data, False
            plist_data = add_pci_root(plist_data, pci_root)
            plist_data["DeviceProperties"]["Add"][pci_root]["model"] = gpu_name
            save_config(plist_path, plist_data)
            print(f"Updated {pci_root} with GPU name '{gpu_name}'.")

        elif choice == '3':
            print("Exiting...")
            break

        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
