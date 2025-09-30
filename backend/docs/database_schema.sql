-- Tabellen für X01
CREATE TABLE IF NOT EXISTS `players_x01` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `is_registered` tinyint(1) NOT NULL DEFAULT 0,
  `average` decimal(5,2) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `games_history_x01` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `player_id` int(11) NOT NULL,
  `match_id` varchar(255) NOT NULL,
  `leg_number` int(11) NOT NULL,
  `leg_average` decimal(5,2) NOT NULL,
  `leg_points` int(11) NOT NULL,
  `leg_darts` int(11) NOT NULL,
  `finished_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `player_id` (`player_id`),
  CONSTRAINT `games_history_x01_ibfk_1` FOREIGN KEY (`player_id`) REFERENCES `players_x01` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Tabellen für Cricket
CREATE TABLE IF NOT EXISTS `players_cricket` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `is_registered` tinyint(1) NOT NULL DEFAULT 0,
  `mpr` decimal(5,2) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `games_history_cricket` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `player_id` int(11) NOT NULL,
  `match_id` varchar(255) NOT NULL,
  `leg_number` int(11) NOT NULL,
  `leg_marks` int(11) NOT NULL,
  `leg_darts` int(11) NOT NULL,
  `finished_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `player_id` (`player_id`),
  CONSTRAINT `games_history_cricket_ibfk_1` FOREIGN KEY (`player_id`) REFERENCES `players_cricket` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Tabellen für Tactics
CREATE TABLE IF NOT EXISTS `players_tactics` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `is_registered` tinyint(1) NOT NULL DEFAULT 0,
  `mpr` decimal(5,2) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `games_history_tactics` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `player_id` int(11) NOT NULL,
  `match_id` varchar(255) NOT NULL,
  `leg_number` int(11) NOT NULL,
  `leg_marks` int(11) NOT NULL,
  `leg_darts` int(11) NOT NULL,
  `finished_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `player_id` (`player_id`),
  CONSTRAINT `games_history_tactics_ibfk_1` FOREIGN KEY (`player_id`) REFERENCES `players_tactics` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Tabellen für ATC
CREATE TABLE IF NOT EXISTS `players_atc` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `is_registered` tinyint(1) NOT NULL DEFAULT 0,
  `hit_rate` decimal(5,4) DEFAULT NULL, -- z.B. 0.7780 für 77.8%
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `games_history_atc` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `player_id` int(11) NOT NULL,
  `match_id` varchar(255) NOT NULL,
  `leg_number` int(11) NOT NULL,
  `leg_hit_rate` decimal(5,4) NOT NULL,
  `leg_darts` int(11) NOT NULL,
  `finished_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `player_id` (`player_id`),
  CONSTRAINT `games_history_atc_ibfk_1` FOREIGN KEY (`player_id`) REFERENCES `players_atc` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Tabellen für Count Up
CREATE TABLE IF NOT EXISTS `players_countup` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `is_registered` tinyint(1) NOT NULL DEFAULT 0,
  `ppr` decimal(5,2) DEFAULT NULL, -- Points Per Round
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `games_history_countup` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `player_id` int(11) NOT NULL,
  `match_id` varchar(255) NOT NULL,
  `leg_number` int(11) NOT NULL,
  `leg_points` int(11) NOT NULL,
  `leg_darts` int(11) NOT NULL,
  `finished_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `player_id` (`player_id`),
  CONSTRAINT `games_history_countup_ibfk_1` FOREIGN KEY (`player_id`) REFERENCES `players_countup` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Tabellen für Segment Training
CREATE TABLE IF NOT EXISTS `players_segment_training` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `is_registered` tinyint(1) NOT NULL DEFAULT 0,
  `hit_rate` decimal(5,4) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `games_history_segment_training` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `player_id` int(11) NOT NULL,
  `match_id` varchar(255) NOT NULL,
  `leg_number` int(11) NOT NULL,
  `leg_hit_rate` decimal(5,4) NOT NULL,
  `leg_darts` int(11) NOT NULL,
  `finished_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `player_id` (`player_id`),
  CONSTRAINT `games_history_segment_training_ibfk_1` FOREIGN KEY (`player_id`) REFERENCES `players_segment_training` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
