import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue



ROVER_MAP = {
    'mega': {
        'package': 'megarover_description',
        'default_choice': 'mega3',
        'choices': ['mega3', 'f120a', 's40a_lb'],
    },
    'mecanum': {
        'package': 'mecanumrover_description',
        'default_choice': 'mecanum3',
        'choices': ['mecanum3', 'g120a', 'g40a_lb'],
    },
    'fwds': {
        'package': 'fwdsrover_description',
        'default_choice': 'x40a',
        'choices': ['x40a', 'x120a'],
    },
}

CONFIGURABLE_PARAMETERS = [
    {
        'name': 'rover',
        'default': 'mega',
        'choices': list(ROVER_MAP.keys()),
        'description': 'Model of rover',
    },
    {
        'name': 'rover_choice',
        'default': '',
        'choices': None,  # 動的なため静的choicesなし
        'description': 'Specific model of rover.\n\t'
                       'Valid choices per rover:\n\t\t' +
                       ',\n\t\t'.join(f"{rover}: {info['choices']} (default: {info['default_choice']})" for rover, info in ROVER_MAP.items()) + 
                       '\n\t\t(If not specified, default is determined by rover type.)',
    },
]


def declare_configurable_parameters(parameters):
    return [
        DeclareLaunchArgument(
            param['name'],
            default_value=param['default'],
            description=param['description'],
            # choicesがNoneの場合は渡さない
            **(({'choices': param['choices']}) if param['choices'] else {}),
        )
        for param in parameters
    ]


def set_configurable_parameters(parameters):
    return {param['name']: LaunchConfiguration(param['name']) for param in parameters}


def launch_setup(context, params, param_name_suffix=''):
    rover_type = LaunchConfiguration('rover').perform(context)
    rover_info = ROVER_MAP[rover_type]

    # rover_choiceが未指定（空文字）の場合はrover_typeに応じたデフォルト値を使用
    rover_choice = LaunchConfiguration('rover_choice').perform(context)
    if not rover_choice:
        rover_choice = rover_info['default_choice']

    # rover_choiceがrover_typeに対して有効か検証
    if rover_choice not in rover_info['choices']:
        raise RuntimeError(
            f"rover_choice '{rover_choice}' is not valid for rover '{rover_type}'. "
            f"Valid choices: {rover_info['choices']}"
        )

    robot_description_path = os.path.join(
        get_package_share_directory(rover_info['package']),
        'urdf',
        f'{rover_choice}.xacro',
    )
    rviz_config_path = os.path.join(
        get_package_share_directory(rover_info['package']),
        'rviz',
        f'{rover_choice}.rviz',
    )

    return [
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher_node',
            parameters=[
                {
                    'robot_description': ParameterValue(
                        Command(['xacro ', robot_description_path]),
                        value_type=str,
                    )
                }
            ],
        ),
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='megarover_rviz2',
            output='screen',
            arguments=['-d', rviz_config_path],
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        declare_configurable_parameters(CONFIGURABLE_PARAMETERS)
        + [
            OpaqueFunction(
                function=launch_setup,
                kwargs={'params': set_configurable_parameters(CONFIGURABLE_PARAMETERS)},
            ),
        ]
    )
