#!/usr/bin/env python3
"""
Launch file: warehouse_explorer.launch.py

Lanza el mundo "warehouse" (con todas sus caracteristicas: actores +
waypoints, plugin path, RViz, etc., tal como en warehouse_simulation.launch.py)
pero en lugar de usar el robot original, spawnea el modelo EXPLORER
(paquete mobile_robot_sim) con solo los sensores que ese modelo tiene
habilitados (no comentados) en su SDF: LIDAR 2D e IMU.

Ubicaciones esperadas:
  - Este launch:  ~/simulation_gz_ws/src/mobile_robot_sim/launch/
  - Modelo:       ~/simulation_gz_ws/src/mobile_robot_sim/models/<model_folder>/model.sdf
  - Mundo:        ~/simulation_gz_ws/src/warehouse_simulator/worlds/<world_name>.sdf
"""
import os
from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    DeclareLaunchArgument,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from ament_index_python.packages import get_package_share_directory, get_package_prefix
from launch_ros.actions import Node


def generate_launch_description():
    # ------------------------------------------------------------------
    # Paquetes y rutas
    # ------------------------------------------------------------------
    pkg_warehouse_share   = get_package_share_directory('warehouse_simulator')
    pkg_warehouse_install = get_package_prefix('warehouse_simulator')
    pkg_robot_share       = get_package_share_directory('mobile_robot_sim')

    world_models_path = os.path.join(pkg_warehouse_share, 'models')
    worlds_path        = os.path.join(pkg_warehouse_share, 'worlds')
    lib_path            = os.path.join(pkg_warehouse_install, 'lib')

    robot_models_path  = os.path.join(pkg_robot_share, 'models')

    yaml_path        = os.path.join(pkg_warehouse_share, 'config', 'actors_waypoints.yaml')
    rviz_config_path = os.path.join(pkg_warehouse_share, 'viz', 'viz_warehouse.rviz')

    # ------------------------------------------------------------------
    # Argumentos de lanzamiento
    # ------------------------------------------------------------------
    gui_arg = DeclareLaunchArgument(
        'gui', default_value='true',
        description='Si es true, lanza Gazebo con GUI. Si es false, server-only (-s).')
    gui = LaunchConfiguration('gui')

    world_name_arg = DeclareLaunchArgument(
        'world_name', default_value='warehouse_full',
        description='Nombre del mundo (sin extension) dentro de warehouse_simulator/worlds/.')
    world_name = LaunchConfiguration('world_name')

    world_file = PythonExpression(["'", world_name, ".sdf'"])
    world_path = PathJoinSubstitution([worlds_path, world_file])

    model_folder_arg = DeclareLaunchArgument(
        'model_folder', default_value='EXPLORER_R2_SENSOR_CONFIG_1',
        description='Carpeta del modelo EXPLORER dentro de mobile_robot_sim/models/.')
    model_folder = LaunchConfiguration('model_folder')
    model_sdf = PathJoinSubstitution([robot_models_path, model_folder, 'model.sdf'])

    robot_name_arg = DeclareLaunchArgument(
        'robot_name', default_value='explorer_r2_sensor_config_1',
        description='Nombre con el que se spawnea el robot en Gazebo.')
    robot_name = LaunchConfiguration('robot_name')

    x_arg = DeclareLaunchArgument('x', default_value='0.0')
    y_arg = DeclareLaunchArgument('y', default_value='0.0')
    z_arg = DeclareLaunchArgument('z', default_value='0.4')
    R_arg = DeclareLaunchArgument('R', default_value='0.0')
    P_arg = DeclareLaunchArgument('P', default_value='0.0')
    Y_arg = DeclareLaunchArgument('Y', default_value='0.0')
    x = LaunchConfiguration('x'); y = LaunchConfiguration('y'); z = LaunchConfiguration('z')
    R = LaunchConfiguration('R'); P = LaunchConfiguration('P'); Y = LaunchConfiguration('Y')

    # ------------------------------------------------------------------
    # Variables de entorno (recursos del mundo + recursos del modelo)
    # ------------------------------------------------------------------
    set_yaml = SetEnvironmentVariable('WAREHOUSE_SIMULATOR_YAML', yaml_path)

    set_plugin_path = SetEnvironmentVariable(
        name='IGN_GAZEBO_SYSTEM_PLUGIN_PATH',
        value=os.pathsep.join(filter(None, [
            os.environ.get('IGN_GAZEBO_SYSTEM_PLUGIN_PATH', ''),
            lib_path,
        ])))

    set_ign_resource = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',
        value=os.pathsep.join(filter(None, [
            os.environ.get('IGN_GAZEBO_RESOURCE_PATH', ''),
            world_models_path,
            robot_models_path,
        ])))

    set_gz_resource = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=os.pathsep.join(filter(None, [
            os.environ.get('GZ_SIM_RESOURCE_PATH', ''),
            world_models_path,
            robot_models_path,
        ])))

    # ------------------------------------------------------------------
    # Gazebo (con y sin GUI) — mundo warehouse completo
    # ------------------------------------------------------------------
    gz_sim_launch_source = PythonLaunchDescriptionSource(
        os.path.join(get_package_share_directory('ros_gz_sim'),
                     'launch', 'gz_sim.launch.py'))

    gz_launch_gui = IncludeLaunchDescription(
        gz_sim_launch_source,
        condition=IfCondition(gui),
        launch_arguments={'gz_args': ['-r ', world_path]}.items())

    gz_launch_headless = IncludeLaunchDescription(
        gz_sim_launch_source,
        condition=UnlessCondition(gui),
        launch_arguments={'gz_args': ['-r -s ', world_path]}.items())

    # ------------------------------------------------------------------
    # Spawn del robot EXPLORER dentro del mundo warehouse
    # ------------------------------------------------------------------
    spawn_robot = Node(
        package='ros_gz_sim', executable='create', name='spawn_explorer',
        output='screen',
        arguments=[
            '-file', model_sdf, '-name', robot_name,
            '-x', x, '-y', y, '-z', z,
            '-R', R, '-P', P, '-Y', Y,
            '-allow_renaming', 'true',
        ])

    # ------------------------------------------------------------------
    # Puente ROS2 <-> Gazebo
    # Solo se puentean los sensores que el EXPLORER tiene habilitados
    # (no comentados) en su SDF: LIDAR 2D e IMU, mas los topicos base
    # (cmd_vel, odom, clock, tf).
    # ------------------------------------------------------------------
    dynamic_pose_topic = [
        '/world/', world_name,
        '/dynamic_pose/info@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
    ]

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        output='screen',
        arguments=[
            # ROS2 -> Gazebo
            '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
            # Gazebo -> ROS2
            '/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
            '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
            '/tf@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
            # IMU
            '/imu@sensor_msgs/msg/Imu[ignition.msgs.IMU',
            # LIDAR 2D
            '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
            # TF dinamico de actores/objetos del mundo warehouse
            dynamic_pose_topic,
        ])

    rviz_node = Node(
        package='rviz2', executable='rviz2', name='rviz2',
        arguments=['-d', rviz_config_path],
        output='screen')

    # ------------------------------------------------------------------
    # TF estaticos — solo para los sensores activos del EXPLORER
    # (offsets deben coincidir con los definidos en el SDF del modelo)
    # ------------------------------------------------------------------
    static_tf_imu = Node(
        package='tf2_ros', executable='static_transform_publisher',
        name='static_tf_imu',
        arguments=[
            '--x', '0.0', '--y', '0.0', '--z', '0.0',
            '--roll', '0.0', '--pitch', '0.0', '--yaw', '0.0',
            '--frame-id', 'base_link', '--child-frame-id', 'imu_link',
        ])

    static_tf_laser2d = Node(
        package='tf2_ros', executable='static_transform_publisher',
        name='static_tf_laser2d',
        arguments=[
            '--x', '0.37', '--y', '0.0', '--z', '0.20',
            '--roll', '0.0', '--pitch', '0.0', '--yaw', '0.0',
            '--frame-id', 'base_link', '--child-frame-id', 'laser_scan_link',
        ])

    return LaunchDescription([
        gui_arg, world_name_arg, model_folder_arg, robot_name_arg,
        x_arg, y_arg, z_arg, R_arg, P_arg, Y_arg,
        set_yaml, set_plugin_path, set_ign_resource, set_gz_resource,
        gz_launch_gui, gz_launch_headless,
        spawn_robot,
        bridge,
        rviz_node,
        static_tf_imu,
        static_tf_laser2d,
    ])