from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetLaunchConfiguration,
)
from launch.conditions import UnlessCondition, IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, SetParameter
from launch_ros.substitutions import FindPackageShare



def generate_launch_description():

    # Package path
    realsense_pkg  = FindPackageShare('realsense2_camera')
    rtabmap_pkg    = FindPackageShare('rtabmap_launch')
    depthimage_pkg = FindPackageShare('depthimage_to_laserscan')

    # RealSense D435i
    realsense_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([realsense_pkg, 'launch', 'rs_launch.py'])
        ),
        launch_arguments={
            'camera_namespace':   '',
            'enable_gyro':        'true',
            'enable_accel':       'true',
            'unite_imu_method':   LaunchConfiguration('unite_imu_method'),
            'align_depth.enable': 'true',
            'enable_sync':        'true',
            'rgb_camera.profile': '640x360x30',
        }.items()
    )

    # Compute quaternion of the IMU
    imu_filter_node = Node(
        package='imu_filter_madgwick',
        executable='imu_filter_madgwick_node',
        output='screen',
        parameters=[{
            'use_mag':     False,
            'world_frame': 'enu',
            'publish_tf':  False,
        }],
        remappings=[('imu/data_raw', '/camera/imu')],
    )

    # depthimage_to_laserscan（localization=true）
    depthimage_to_laserscan_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([depthimage_pkg, 'launch', 'depthimage_to_laserscan-launch.py'])
        ),
        condition=IfCondition(LaunchConfiguration('localization'))
    )

    # RTAB-MAP
    rtabmap_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([rtabmap_pkg, 'launch', 'rtabmap.launch.py'])
        ),
        launch_arguments={
            'localization':       LaunchConfiguration('localization'),
            'approx_sync':        'true',
            'rgb_topic':          '/camera/color/image_raw',
            'depth_topic':        '/camera/aligned_depth_to_color/image_raw',
            'camera_info_topic':  '/camera/color/camera_info',
            'frame_id':           'base_footprint',
            'database_path':      LaunchConfiguration('database_path'),
            'rtabmap_viz':        LaunchConfiguration('rtabmap_viz'),
            'rviz':               LaunchConfiguration('rviz'),
        }.items()
    )

    return LaunchDescription([
        # Arguments
        # RTAB-MAP
        DeclareLaunchArgument('localization',  default_value='false',              description='true: localization mode, false: mapping mode'),
        DeclareLaunchArgument('database_path', default_value='~/.ros/rtabmap.db', description='Where is the map saved/loaded.'),
        DeclareLaunchArgument('rtabmap_viz',   default_value='true',              description='Launch RTAB-MAP UI.'),
        DeclareLaunchArgument('rviz',          default_value='true',             description='Launch RVIZ.'),

        SetLaunchConfiguration(name='rtabmap_args', value='--delete_db_on_start', condition=UnlessCondition(LaunchConfiguration('localization'))),

        # IMU Madgwick filter
        DeclareLaunchArgument('unite_imu_method', default_value='2', description='0-None, 1-copy, 2-linear_interpolation.'),
        
        # Make sure IR emitter is enabled
        SetParameter(name='depth_module.emitter_enabled', value=1),

        # Startup of each node/launch
        realsense_launch,
        imu_filter_node,
        depthimage_to_laserscan_launch,
        rtabmap_launch,
    ])