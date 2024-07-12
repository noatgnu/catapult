import yaml
import click

def diann_yaml_parser(yaml_path):
    with open(yaml_path, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
            commands = [config["diann_path"]]
            for key, value in config.items():
                if key != "diann_path" and key !="ready":
                    key = key.replace("_", "-")
                    if value is not None:
                        if key == "channels":
                            if isinstance(value, list):
                                commands.append(f'--{key}')
                                commands.append("; ".join(value))
                            elif isinstance(value, str):
                                commands.append(f'--{key}')
                                commands.append(value)
                        elif isinstance(value, bool):
                            if value:
                                commands.append(f'--{key}')
                        elif isinstance(value, list):
                            if key == "unimod":
                                for item in value:
                                    commands.append(f'--unimod{str(item)}')
                            elif key == "temp":
                                commands.append(f'--temp')
                                commands.append(str(value))
                            elif key == "f":
                                for item in value:
                                    commands.append(f'--{key}')
                                    commands.append(str(item))
                            elif key == "out":
                                commands.append(f'--out')
                                commands.append(str(value))

                            else:
                                for item in value:
                                    commands.append(f'--{key}')
                                    commands.append(str(item))
                        else:
                            commands.append(f'--{key}')
                            commands.append(str(value))
            return " ".join(commands)
        except yaml.YAMLError as exc:
            print(exc)
            return None

@click.command()
@click.option("--yaml_path", "-y", help="Path to the yaml file")
def main(yaml_path):
    print(diann_yaml_parser(yaml_path))

if __name__ == "__main__":
    main()