#!/usr/bin/python3

# written by sqall
# twitter: https://twitter.com/sqall01
# blog: https://h4des.org
# github: https://github.com/sqall01
#
# Licensed under the GNU Affero General Public License, version 3.

import threading
from typing import Dict, List
from ..localObjects import Alert, AlertLevel, Manager, Node, Sensor, SensorAlert, Option


class SystemData:

    def __init__(self):

        # key: type
        self._options = dict()  # type: Dict[str, Option]

        # key: nodeId
        self._nodes = dict()  # type: Dict[int, Node]

        # key: sensorId
        self._sensors = dict()  # type: Dict[int, Sensor]

        # key: managerId
        self._managers = dict()  # type: Dict[int, Manager]

        # key: alertId
        self._alerts = dict()  # type: Dict[int, Alert]

        # TODO: list perhaps better? How long do we store sensorAlerts? Perhaps give function to delete all sensor alerts older than X?
        self._sensor_alerts = dict()

        # key: level
        self._alert_levels = dict()  # type: Dict[int, AlertLevel]

        self._data_lock = threading.Lock()

    def _alert_sanity_check(self, alert: Alert):
        # Does corresponding node exist?
        if alert.nodeId not in self._nodes.keys():
            raise ValueError("Node %d for corresponding alert %d does not exist."
                             % (alert.nodeId, alert.alertId))

        # Does corresponding node have correct type?
        if self._nodes[alert.nodeId].nodeType.lower() != "alert":
            raise ValueError("Node %d not of correct type for corresponding alert %d."
                             % (alert.nodeId, alert.alertId))

        # Do the alert levels for this alert exist?
        for alert_level in alert.alertLevels:
            if alert_level not in self._alert_levels.keys():
                raise ValueError("Alert Level %d does not exist for alert %d."
                                 % (alert_level, alert.alertId))

    def _manager_sanity_check(self, manager: Manager):
        # Does corresponding node exist?
        if manager.nodeId not in self._nodes.keys():
            raise ValueError("Node %d for corresponding manager %d does not exist."
                             % (manager.nodeId, manager.managerId))

        # Does corresponding node have correct type?
        if self._nodes[manager.nodeId].nodeType.lower() != "manager":
            raise ValueError("Node %d not of correct type for corresponding manager %d."
                             % (manager.nodeId, manager.managerId))

    def _sensor_sanity_check(self, sensor: Sensor):
        # Does corresponding node exist?
        if sensor.nodeId not in self._nodes.keys():
            raise ValueError("Node %d for corresponding sensor %d does not exist."
                             % (sensor.nodeId, sensor.sensorId))

        # Does corresponding node have correct type?
        if self._nodes[sensor.nodeId].nodeType.lower() != "sensor":
            raise ValueError("Node %d not of correct type for corresponding sensor %d."
                             % (sensor.nodeId, sensor.sensorId))

        # Do the alert levels for this alert exist?
        for alert_level in sensor.alertLevels:
            if alert_level not in self._alert_levels.keys():
                raise ValueError("Alert Level %d does not exist for sensor %d."
                                 % (alert_level, sensor.sensorId))

    def get_alerts_list(self) -> List[Alert]:
        """
        Gets list of all alert objects.
        :return: List of objects.
        """
        with self._data_lock:
            return list(self._alerts.values())

    def get_alert_levels_list(self) -> List[AlertLevel]:
        """
        Gets list of all alert level objects.
        :return: List of objects.
        """
        with self._data_lock:
            return list(self._alert_levels.values())

    def get_managers_list(self) -> List[Manager]:
        """
        Gets list of all manager objects.
        :return: List of objects.
        """
        with self._data_lock:
            return list(self._managers.values())

    def get_nodes_list(self) -> List[Node]:
        """
        Gets list of all node objects.
        :return: List of objects.
        """
        with self._data_lock:
            return list(self._nodes.values())

    def get_options_list(self) -> List[Option]:
        """
        Gets list of all option objects.
        :return: List of objects.
        """
        with self._data_lock:
            return list(self._options.values())

    def get_sensors_list(self) -> List[Sensor]:
        """
        Gets list of all sensor objects.
        :return: List of objects.
        """
        with self._data_lock:
            return list(self._sensors.values())

    def update_alert(self, alert: Alert):
        """
        Updates the given alert data.
        :param alert:
        """
        with self._data_lock:

            # Add alert object if it does not exist yet.
            if alert.alertId not in self._alerts.keys():
                self._alert_sanity_check(alert)
                self._alerts[alert.alertId] = alert

            # Update alert object data.
            else:
                self._alert_sanity_check(alert)

                # Do update of data instead of just using new alert object
                # to make sure others can work on the same object.
                self._alerts[alert.alertId].deepCopy(alert)

    def update_alert_level(self, alert_level: AlertLevel):
        """
        Updates the given alert level data.
        :param alert_level:
        """
        with self._data_lock:

            # Add alert level object if it does not exist yet.
            if alert_level.level not in self._alert_levels.keys():
                self._alert_levels[alert_level.level] = alert_level

            # Update alert level object data.
            else:

                # Do update of data instead of just using new alert level object
                # to make sure others can work on the same object.
                self._alert_levels[alert_level.level].deepCopy(alert_level)

    def update_manager(self, manager: Manager):
        """
        Updates the given manager data.
        :param manager:
        """
        with self._data_lock:

            # Add manager object if it does not exist yet.
            if manager.managerId not in self._managers.keys():
                self._manager_sanity_check(manager)
                self._managers[manager.managerId] = manager

            # Update manager object data.
            else:
                self._manager_sanity_check(manager)

                # Do update of data instead of just using new manager object
                # to make sure others can work on the same object.
                self._managers[manager.managerId].deepCopy(manager)

    def update_node(self, node: Node):
        """
        Updates the given node data.
        :param node:
        """
        with self._data_lock:

            # Add node object if it does not exist yet.
            if node.nodeId not in self._nodes.keys():
                self._nodes[node.nodeId] = node

            # Update node object data.
            else:

                # If the type of the node has changed remove related objects.
                curr_node = self._nodes[node.nodeId]
                if curr_node.nodeType != node.nodeType:
                    if curr_node.nodeType.lower() == "alert":
                        to_remove = []
                        for alert_id, alert in self._alerts.items():
                            if alert.nodeId == curr_node.nodeId:
                                to_remove.append(alert_id)
                        for alert_id in to_remove:
                            del self._alerts[alert_id]

                    elif curr_node.nodeType.lower() == "manager":
                        to_remove = []
                        for manager_id, manager in self._managers.items():
                            if manager.nodeId == curr_node.nodeId:
                                to_remove.append(manager_id)
                        for manager_id in to_remove:
                            del self._managers[manager_id]

                    elif curr_node.nodeType.lower() == "sensor":
                        to_remove = []
                        for sensor_id, sensor in self._sensors.items():
                            if sensor.nodeId == curr_node.nodeId:
                                to_remove.append(sensor_id)
                        for sensor_id in to_remove:
                            del self._sensors[sensor_id]

                # Do update of data instead of just using new node object
                # to make sure others can work on the same object.
                self._nodes[node.nodeId].deepCopy(node)

    def update_option(self, option: Option):
        """
        Updates the given option data.
        :param option:
        :return: success of failure
        """
        with self._data_lock:
            # Just change value, does not make a difference if it already exists or not.
            self._options[option.type] = option

    def update_sensor(self, sensor: Sensor):
        """
        Updates the given sensor data.
        :param sensor:
        """
        with self._data_lock:

            # Add sensor object if it does not exist yet.
            if sensor.sensorId not in self._sensors.keys():
                self._sensor_sanity_check(sensor)
                self._sensors[sensor.sensorId] = sensor

            # Update sensor object data.
            else:
                self._sensor_sanity_check(sensor)

                # Do update of data instead of just using new sensor object
                # to make sure others can work on the same object.
                self._sensors[sensor.sensorId].deepCopy(sensor)




# TODO
# * handle storage of AlertR data
# * only have atomic interfaces (update, delete, get) and let big picture like "node X was deleted" be handled by eventmanager
# * lock data when accessed
# * give interfaces to get copy of data (perhaps also list of Node/Alert/... to be compatible with old managers?)
# * test cases to check if it works
#   * edge case node changes type