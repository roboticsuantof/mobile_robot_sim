#!/usr/bin/env python3
"""
Launch file: spawn_ugv_csiro.launch.py
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    IncludeLaunchDescription,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    # ----- Paquetes y rutas -----
    pkg_robot_simulator = get_package_share_directory('mobile_robot_sim')
    pkg_ros_gz_sim      = get_package_share_directory('ros_gz_sim')
    models_path = os.path.join(pkg_robot_simulator, 'models')
    worlds_path = os.path.join(pkg_robot_simulator, 'worlds')

    # ▶ Ruta al YAML de parámetros del controlador
    controller_params = os.path.join(
        pkg_robot_simulator, 'config', 'controller_params.yaml')

    # ----- Argumentos -----
    declare_model_folder = DeclareLaunchArgument(
        'model_folder', default_value='EXPLORER_R2_SENSOR_CONFIG_1',
        description='Carpeta del modelo dentro de models/ a spawnear')
    declare_world_folder = DeclareLaunchArgument(
        'world_folder', default_value='tugbot_depot',
        description='Subcarpeta dentro de worlds/ donde está el .sdf del mundo')
    declare_world = DeclareLaunchArgument(
        'world', default_value='tugbot_depot.sdf',
        description='Archivo .sdf del mundo dentro de worlds/<world_folder>/')
    declare_robot_name = DeclareLaunchArgument(
        'robot_name', default_value='explorer_r2_sensor_config_1')
    # declare_x = DeclareLaunchArgument('x', default_value='-8.0') #For Rubicon World
    declare_x = DeclareLaunchArgument('x', default_value='0.0') # For empty World
    declare_y = DeclareLaunchArgument('y', default_value='-0.0')
    # declare_z = DeclareLaunchArgument('z', default_value='4.4') #For Rubicon world
    declare_z = DeclareLaunchArgument('z', default_value='0.4') # For empty World
    declare_R = DeclareLaunchArgument('R', default_value='0.0')
    declare_P = DeclareLaunchArgument('P', default_value='0.0')
    declare_Y = DeclareLaunchArgument('Y', default_value='0.0')
    declare_gui = DeclareLaunchArgument('gui', default_value='true')

    model_folder = LaunchConfiguration('model_folder')
    world_folder = LaunchConfiguration('world_folder')
    world        = LaunchConfiguration('world')
    robot_name   = LaunchConfiguration('robot_name')
    x = LaunchConfiguration('x'); y = LaunchConfiguration('y'); z = LaunchConfiguration('z')
    R = LaunchConfiguration('R'); P = LaunchConfiguration('P'); Y = LaunchConfiguration('Y')

    # ----- Rutas a SDFs -----
    model_sdf = PathJoinSubstitution([models_path, model_folder, 'model.sdf'])
    world_sdf = PathJoinSubstitution([worlds_path, world_folder, world])

    gz_args_gui      = [world_sdf, ' -r -v 4']
    gz_args_headless = [world_sdf, ' -r -v 4 -s']

    # ----- Variables de entorno -----
    env_actions = [
        AppendEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', models_path),
        AppendEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', worlds_path),
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH',     models_path),
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH',     worlds_path),
        AppendEnvironmentVariable(
            'GZ_SIM_RESOURCE_PATH',
            PathJoinSubstitution([worlds_path, world_folder])),
        AppendEnvironmentVariable(
            'IGN_GAZEBO_RESOURCE_PATH',
            PathJoinSubstitution([worlds_path, world_folder])),
    ]

    # ----- Lanzar Gazebo -----
    gz_sim_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': gz_args_gui}.items(),
        condition=IfCondition(LaunchConfiguration('gui')),
    )
    gz_sim_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': gz_args_headless}.items(),
        condition=UnlessCondition(LaunchConfiguration('gui')),
    )

    # ----- Spawn del robot -----
    spawn_robot = Node(
        package='ros_gz_sim', executable='create', name='spawn_robot',
        output='screen',
        arguments=[
            '-file', model_sdf, '-name', robot_name,
            '-x', x, '-y', y, '-z', z,
            '-R', R, '-P', P, '-Y', Y,
            '-allow_renaming', 'true',
        ],
    )

    # ----- Puente ROS2 <-> Ignition -----
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        output='screen',
        arguments=[
            # ROS2 -> Ignition
            '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
            # Ignition -> ROS2
            '/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
            '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
            # TF dinámico: odom -> base_link
            '/tf@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
            # IMU
            '/imu@sensor_msgs/msg/Imu[ignition.msgs.IMU',
            # GPS / NavSat
            '/navsat@sensor_msgs/msg/NavSatFix[ignition.msgs.NavSat',
            # Lidar 3D tipo PointCloud
            # '/PointCloud/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
            # ── LaserScan 2D ──────────────────────────────────────────────────
            '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
            # ──────────────────────────────────────────────────────────────────
            # Cámara frontal RGBD
            # '/camera_front/image@sensor_msgs/msg/Image[ignition.msgs.Image',
            # '/camera_front/depth_image@sensor_msgs/msg/Image[ignition.msgs.Image',
            # '/camera_front/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
            # '/camera_front/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
            # Cámara izquierda RGBD
            # '/camera_left/image@sensor_msgs/msg/Image[ignition.msgs.Image',
            # '/camera_left/depth_image@sensor_msgs/msg/Image[ignition.msgs.Image',
            # '/camera_left/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
            # '/camera_left/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
            # Cámara trasera RGBD
            # '/camera_rear/image@sensor_msgs/msg/Image[ignition.msgs.Image',
            # '/camera_rear/depth_image@sensor_msgs/msg/Image[ignition.msgs.Image',
            # '/camera_rear/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
            # '/camera_rear/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
            # Cámara derecha RGBD
            # '/camera_right/image@sensor_msgs/msg/Image[ignition.msgs.Image',
            # '/camera_right/depth_image@sensor_msgs/msg/Image[ignition.msgs.Image',
            # '/camera_right/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
            # '/camera_right/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
            '/world/tugbot_depot/dynamic_pose/info@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
        ],
    )

    # ▶ Nodo controlador de posición + orientación
    # name debe coincidir con la clave raíz del YAML: 'ugv_position_controller'
    # position_controller = Node(
    #     package='mobile_robot_sim',
    #     executable='position_controller',
    #     name='ugv_position_controller',
    #     output='screen',
    #     emulate_tty=True,
    #     parameters=[controller_params],
    # )

    # ----- TF estáticos -----
    static_tf_imu = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_imu',
        arguments=[
            '--x', '0.0', '--y', '0.0', '--z', '0.0',
            '--roll', '0.0', '--pitch', '0.0', '--yaw', '0.0',
            '--frame-id', 'base_link',
            '--child-frame-id', 'imu_link'
        ],
    )

    static_tf_gps = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_gps',
        arguments=[
            '--x', '0.0', '--y', '0.0', '--z', '0.0',
            '--roll', '0.0', '--pitch', '0.0', '--yaw', '0.0',
            '--frame-id', 'base_link',
            '--child-frame-id', 'gps_link'
        ],
    )

    # static_tf_lidar = Node(
    #     package='tf2_ros',
    #     executable='static_transform_publisher',
    #     name='static_tf_lidar',
    #     arguments=[
    #         '--x', '0.37', '--y', '0.0', '--z', '0.55',
    #         '--roll', '0.0', '--pitch', '0.0', '--yaw', '0.0',
    #         '--frame-id', 'base_link',
    #         '--child-frame-id', 'lidar_link'
    #     ],
    # )

    # ── TF estático: LaserScan 2D ────────────────────────────────────────────
    # Pose igual a la definida en el SDF: x=0.37, y=0.0, z=0.20
    static_tf_laser2d = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_laser2d',
        arguments=[
            '--x', '0.37', '--y', '0.0', '--z', '0.20',
            '--roll', '0.0', '--pitch', '0.0', '--yaw', '0.0',
            '--frame-id', 'base_link',
            '--child-frame-id', 'laser_scan_link'
        ],
    )
    # ────────────────────────────────────────────────────────────────────────

    # static_tf_camera_front = Node(
    #     package='tf2_ros',
    #     executable='static_transform_publisher',
    #     name='static_tf_camera_front',
    #     arguments=[
    #         '--x', '0.565', '--y', '0.0', '--z', '0.245',
    #         '--roll', '0.0', '--pitch', '0.0', '--yaw', '0.0',
    #         '--frame-id', 'base_link',
    #         '--child-frame-id', 'camera_front_link'
    #     ],
    # )

    # static_tf_camera_left = Node(
    #     package='tf2_ros',
    #     executable='static_transform_publisher',
    #     name='static_tf_camera_left',
    #     arguments=[
    #         '--x', '0.365', '--y', '0.133', '--z', '0.426',
    #         '--roll', '0.0', '--pitch', '0.0', '--yaw', '1.5707963267948966',
    #         '--frame-id', 'base_link',
    #         '--child-frame-id', 'camera_left_link'
    #     ],
    # )

    # static_tf_camera_rear = Node(
    #     package='tf2_ros',
    #     executable='static_transform_publisher',
    #     name='static_tf_camera_rear',
    #     arguments=[
    #         '--x', '0.25', '--y', '0.0', '--z', '0.432',
    #         '--roll', '0.0', '--pitch', '0.0', '--yaw', '3.1415926535897931',
    #         '--frame-id', 'base_link',
    #         '--child-frame-id', 'camera_rear_link'
    #     ],
    # )

    # static_tf_camera_right = Node(
    #     package='tf2_ros',
    #     executable='static_transform_publisher',
    #     name='static_tf_camera_right',
    #     arguments=[
    #         '--x', '0.365', '--y', '-0.133', '--z', '0.426',
    #         '--roll', '0.0', '--pitch', '0.0', '--yaw', '-1.5707963267948966',
    #         '--frame-id', 'base_link',
    #         '--child-frame-id', 'camera_right_link'
    #     ],
    # )

    # static_tf_camera_front_optical = Node(
    #     package='tf2_ros',
    #     executable='static_transform_publisher',
    #     name='static_tf_camera_front_optical',
    #     arguments=[
    #         '--x', '0.0', '--y', '0.0', '--z', '0.0',
    #         '--roll', '-1.5707963267948966',
    #         '--pitch', '0.0',
    #         '--yaw', '-1.5707963267948966',
    #         '--frame-id', 'camera_front_link',
    #         '--child-frame-id', 'camera_front_optical_frame'
    #     ],
    # )

    # static_tf_camera_left_optical = Node(
    #     package='tf2_ros',
    #     executable='static_transform_publisher',
    #     name='static_tf_camera_left_optical',
    #     arguments=[
    #         '--x', '0.0', '--y', '0.0', '--z', '0.0',
    #         '--roll', '-1.5707963267948966',
    #         '--pitch', '0.0',
    #         '--yaw', '-1.5707963267948966',
    #         '--frame-id', 'camera_left_link',
    #         '--child-frame-id', 'camera_left_optical_frame'
    #     ],
    # )

    # static_tf_camera_rear_optical = Node(
    #     package='tf2_ros',
    #     executable='static_transform_publisher',
    #     name='static_tf_camera_rear_optical',
    #     arguments=[
    #         '--x', '0.0', '--y', '0.0', '--z', '0.0',
    #         '--roll', '-1.5707963267948966',
    #         '--pitch', '0.0',
    #         '--yaw', '-1.5707963267948966',
    #         '--frame-id', 'camera_rear_link',
    #         '--child-frame-id', 'camera_rear_optical_frame'
    #     ],
    # )

    # static_tf_camera_right_optical = Node(
    #     package='tf2_ros',
    #     executable='static_transform_publisher',
    #     name='static_tf_camera_right_optical',
    #     arguments=[
    #         '--x', '0.0', '--y', '0.0', '--z', '0.0',
    #         '--roll', '-1.5707963267948966',
    #         '--pitch', '0.0',
    #         '--yaw', '-1.5707963267948966',
    #         '--frame-id', 'camera_right_link',
    #         '--child-frame-id', 'camera_right_optical_frame'
    #     ],
    # )

    return LaunchDescription([
        declare_model_folder, declare_world_folder, declare_world,
        declare_robot_name,
        declare_x, declare_y, declare_z,
        declare_R, declare_P, declare_Y,
        declare_gui,
        *env_actions,
        gz_sim_gui, gz_sim_headless,
        spawn_robot,
        bridge,
        # position_controller,

        static_tf_imu,
        static_tf_gps,
        # static_tf_lidar,
        static_tf_laser2d,          # ← LaserScan 2D
        # static_tf_camera_front,
        # static_tf_camera_left,
        # static_tf_camera_rear,
        # static_tf_camera_right,
        # static_tf_camera_front_optical,
        # static_tf_camera_left_optical,
        # static_tf_camera_rear_optical,
        # static_tf_camera_right_optical,
    ])