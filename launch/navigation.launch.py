import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, GroupAction, IncludeLaunchDescription,
    OpaqueFunction, SetEnvironmentVariable, SetLaunchConfiguration
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import LoadComposableNodes, Node, PushRosNamespace
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare
from nav2_common.launch import RewrittenYaml



def _resolve_params_file(context, bringup_dir):
    params_file = LaunchConfiguration('params_file').perform(context)
    rover = LaunchConfiguration('rover').perform(context)
    if params_file:
        selected = params_file
    elif rover == 'mecanum':
        selected = os.path.join(bringup_dir, 'config', 'mecanumrover_nav2_params.yaml')
    elif rover == 'fwds':
        selected = os.path.join(bringup_dir, 'config', 'fwdsrover_nav2_params.yaml')
    else:
        selected = os.path.join(bringup_dir, 'config', 'megarover_nav2_params.yaml')
    return [SetLaunchConfiguration('selected_params_file', selected)]

def generate_launch_description():
    bringup_dir = get_package_share_directory('vs_rover_depthcam_samples')

    # ── LaunchConfiguration ──
    namespace           = LaunchConfiguration('namespace')
    use_namespace       = LaunchConfiguration('use_namespace')
    rover               = LaunchConfiguration('rover')
    use_sim_time        = LaunchConfiguration('use_sim_time')
    params_file         = LaunchConfiguration('params_file')
    autostart           = LaunchConfiguration('autostart')
    use_composition     = LaunchConfiguration('use_composition')
    container_name      = LaunchConfiguration('container_name')
    container_name_full = (namespace, '/', container_name)
    use_respawn         = LaunchConfiguration('use_respawn')
    log_level           = LaunchConfiguration('log_level')
    use_rviz            = LaunchConfiguration('use_rviz')
    rvizconfig          = LaunchConfiguration('rvizconfig')
    selected_params_file = LaunchConfiguration('selected_params_file')

    lifecycle_nodes = [
        'controller_server',
        'smoother_server',
        'planner_server',
        'behavior_server',
        'bt_navigator',
        'waypoint_follower',
        'velocity_smoother',
    ]

    tf_remappings = [
        ('/tf',        'tf'),
        ('/tf_static', 'tf_static'),
    ]

    nav2_remappings = tf_remappings + [('/cmd_vel', '/rover_twist')]

    param_substitutions = {
        'use_sim_time': use_sim_time,
        'autostart':    autostart,
    }
    configured_params = RewrittenYaml(
        source_file=selected_params_file,
        root_key=namespace,
        param_rewrites=param_substitutions,
        convert_types=True,
    )

    # ════════════════════════════════════════════
    # bringup_group
    # ════════════════════════════════════════════
    bringup_group = GroupAction([

        PushRosNamespace(
            condition=IfCondition(use_namespace),
            namespace=namespace,
        ),

        Node(
            condition=IfCondition(use_composition),
            name='nav2_container',
            package='rclcpp_components',
            executable='component_container_isolated',
            parameters=[
                selected_params_file,
                {'autostart':     autostart},
                {'use_sim_time':  use_sim_time},
            ],
            arguments=['--ros-args', '--log-level', log_level],
            remappings=tf_remappings,
            output='screen',
        ),

        GroupAction(
            condition=IfCondition(PythonExpression(['not ', use_composition])),
            actions=[
                Node(
                    package='nav2_controller',
                    executable='controller_server',
                    output='screen',
                    respawn=use_respawn,
                    respawn_delay=2.0,
                    parameters=[configured_params],
                    arguments=['--ros-args', '--log-level', log_level],
                    remappings=nav2_remappings + [('cmd_vel', 'cmd_vel_nav')],
                ),
                Node(
                    package='nav2_smoother',
                    executable='smoother_server',
                    name='smoother_server',
                    output='screen',
                    respawn=use_respawn,
                    respawn_delay=2.0,
                    parameters=[configured_params],
                    arguments=['--ros-args', '--log-level', log_level],
                    remappings=nav2_remappings,
                ),
                Node(
                    package='nav2_planner',
                    executable='planner_server',
                    name='planner_server',
                    output='screen',
                    respawn=use_respawn,
                    respawn_delay=2.0,
                    parameters=[configured_params],
                    arguments=['--ros-args', '--log-level', log_level],
                    remappings=nav2_remappings,
                ),
                Node(
                    package='nav2_behaviors',
                    executable='behavior_server',
                    name='behavior_server',
                    output='screen',
                    respawn=use_respawn,
                    respawn_delay=2.0,
                    parameters=[configured_params],
                    arguments=['--ros-args', '--log-level', log_level],
                    remappings=nav2_remappings,
                ),
                Node(
                    package='nav2_bt_navigator',
                    executable='bt_navigator',
                    name='bt_navigator',
                    output='screen',
                    respawn=use_respawn,
                    respawn_delay=2.0,
                    parameters=[configured_params],
                    arguments=['--ros-args', '--log-level', log_level],
                    remappings=nav2_remappings,
                ),
                Node(
                    package='nav2_waypoint_follower',
                    executable='waypoint_follower',
                    name='waypoint_follower',
                    output='screen',
                    respawn=use_respawn,
                    respawn_delay=2.0,
                    parameters=[configured_params],
                    arguments=['--ros-args', '--log-level', log_level],
                    remappings=nav2_remappings,
                ),
                Node(
                    package='nav2_velocity_smoother',
                    executable='velocity_smoother',
                    name='velocity_smoother',
                    output='screen',
                    respawn=use_respawn,
                    respawn_delay=2.0,
                    parameters=[configured_params],
                    arguments=['--ros-args', '--log-level', log_level],
                    remappings=nav2_remappings + [
                        ('cmd_vel',          'cmd_vel_nav'),
                        ('cmd_vel_smoothed', 'cmd_vel'),
                    ],
                ),
                Node(
                    package='nav2_lifecycle_manager',
                    executable='lifecycle_manager',
                    name='lifecycle_manager_navigation',
                    output='screen',
                    arguments=['--ros-args', '--log-level', log_level],
                    parameters=[
                        {'use_sim_time': use_sim_time},
                        {'autostart':    autostart},
                        {'node_names':   lifecycle_nodes},
                    ],
                ),
            ],
        ),

        LoadComposableNodes(
            condition=IfCondition(use_composition),
            target_container=container_name_full,
            composable_node_descriptions=[
                ComposableNode(
                    package='nav2_controller',
                    plugin='nav2_controller::ControllerServer',
                    name='controller_server',
                    parameters=[configured_params],
                    remappings=nav2_remappings + [('cmd_vel', 'cmd_vel_nav')],
                ),
                ComposableNode(
                    package='nav2_smoother',
                    plugin='nav2_smoother::SmootherServer',
                    name='smoother_server',
                    parameters=[configured_params],
                    remappings=nav2_remappings,
                ),
                ComposableNode(
                    package='nav2_planner',
                    plugin='nav2_planner::PlannerServer',
                    name='planner_server',
                    parameters=[configured_params],
                    remappings=nav2_remappings,
                ),
                ComposableNode(
                    package='nav2_behaviors',
                    plugin='behavior_server::BehaviorServer',
                    name='behavior_server',
                    parameters=[configured_params],
                    remappings=nav2_remappings,
                ),
                ComposableNode(
                    package='nav2_bt_navigator',
                    plugin='nav2_bt_navigator::BtNavigator',
                    name='bt_navigator',
                    parameters=[configured_params],
                    remappings=nav2_remappings,
                ),
                ComposableNode(
                    package='nav2_waypoint_follower',
                    plugin='nav2_waypoint_follower::WaypointFollower',
                    name='waypoint_follower',
                    parameters=[configured_params],
                    remappings=nav2_remappings,
                ),
                ComposableNode(
                    package='nav2_velocity_smoother',
                    plugin='nav2_velocity_smoother::VelocitySmoother',
                    name='velocity_smoother',
                    parameters=[configured_params],
                    remappings=nav2_remappings + [
                        ('cmd_vel',          'cmd_vel_nav'),
                        ('cmd_vel_smoothed', 'cmd_vel'),
                    ],
                ),
                ComposableNode(
                    package='nav2_lifecycle_manager',
                    plugin='nav2_lifecycle_manager::LifecycleManager',
                    name='lifecycle_manager_navigation',
                    parameters=[{
                        'use_sim_time': use_sim_time,
                        'autostart':    autostart,
                        'node_names':   lifecycle_nodes,
                    }],
                ),
            ],
        ),
    ])

    rviz_node = Node(
        condition=IfCondition(use_rviz),
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rvizconfig],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    return LaunchDescription([

        DeclareLaunchArgument('rover',           default_value='mega',           description='Rover type: mega / mecanum / fwds'),
        DeclareLaunchArgument('namespace',       default_value='',               description='Top-level namespace'),
        DeclareLaunchArgument('use_namespace',   default_value='False',          description='Whether to apply namespace'),
        DeclareLaunchArgument('use_sim_time',    default_value='False',          description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument('params_file',     default_value='',               description='Optional full path to nav2 params file. Empty = auto by rover'),
        DeclareLaunchArgument('autostart',       default_value='true',           description='Automatically startup the nav2 stack'),
        DeclareLaunchArgument('use_composition', default_value='True',           description='Whether to use composed bringup'),
        DeclareLaunchArgument('container_name',  default_value='nav2_container', description='Container name when composition is enabled'),
        DeclareLaunchArgument('use_respawn',     default_value='False',          description='Whether to respawn if a node crashes'),
        DeclareLaunchArgument('log_level',       default_value='info',           description='log level'),
        DeclareLaunchArgument('use_rviz',        default_value='true',           description='Launch RViz2'),
        DeclareLaunchArgument('rvizconfig',
            default_value=PathJoinSubstitution(
                [FindPackageShare('vs_rover_depthcam_samples'), 'rviz', 'navigation.rviz']
            ),
            description='Absolute path to rviz config file',
        ),

        SetLaunchConfiguration('selected_params_file', ''),
        OpaqueFunction(function=lambda context: _resolve_params_file(context, bringup_dir)),

        SetEnvironmentVariable('RCUTILS_LOGGING_BUFFERED_STREAM', '1'),

        bringup_group,
        rviz_node,
    ])