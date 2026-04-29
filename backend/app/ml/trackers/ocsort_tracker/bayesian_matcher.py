# -*- coding: utf-8 -*-
# @Time : 2026-03-31
# @Author : 魏继勇
# @File : bayesian_matcher.py
# @Description : 轻量化贝叶斯匹配器 - 支持距离+IoU双证据融合

from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class StableTrack:
    """稳定轨迹"""
    track_id: int
    center_x: int
    center_y: int
    box_w: int
    box_h: int
    lost_frames: int
    class_id: int
    label: str
    hit_count: int


class BayesianMatcher:
    """
    轻量化贝叶斯匹配器 - 支持距离+IoU双证据融合
    
    匹配公式（加权贝叶斯）：
      Score_old = w_dist × P(H0)×P(D_dist|H0) + w_iou × P(H0)×P(D_iou|H0)
      Score_new = w_dist × P(H1)×P(D_dist|H1) + w_iou × P(H1)×P(D_iou|H1)
    
    特性：
    - 全整数运算，无浮点数除法（IoU用乘100避免小数）
    - 无开方，无指数函数
    - 内存占用极低
    """
    
    def __init__(self, config: dict):
        self.enable_iou = config.get('enable_iou', True)
        
        self.sigma_sq = config.get('sigma_sq', 120 * 120)
        self.max_lost_frames = config.get('max_lost_frames', 200)
        self.min_stable_frames = config.get('min_stable_frames', 3)
        
        self.prior_lost_1 = config.get('prior_lost_1', 85)
        self.prior_lost_2_3 = config.get('prior_lost_2_3', 60)
        self.prior_lost_4_8 = config.get('prior_lost_4_8', 30)
        self.prior_lost_9_plus = config.get('prior_lost_9_plus', 10)
        
        self.dist_likelihood_very_near = config.get('dist_likelihood_very_near', 92)
        self.dist_likelihood_near = config.get('dist_likelihood_near', 65)
        self.dist_likelihood_medium = config.get('dist_likelihood_medium', 35)
        self.dist_likelihood_far = config.get('dist_likelihood_far', 12)
        
        self.iou_weight = config.get('iou_weight', 40)
        self.iou_min_threshold = config.get('iou_min_threshold', 3)
        
        self.iou_likelihood_very_high = config.get('iou_likelihood_very_high', 95)
        self.iou_likelihood_high = config.get('iou_likelihood_high', 75)
        self.iou_likelihood_medium = config.get('iou_likelihood_medium', 45)
        self.iou_likelihood_low = config.get('iou_likelihood_low', 15)
        self.iou_likelihood_none = config.get('iou_likelihood_none', 5)
        
        self.adaptive_sigma = config.get('adaptive_sigma', True)
        self.sigma_increase_threshold = config.get('sigma_increase_threshold', 4)
        self.sigma_max = config.get('sigma_max', 180 * 180)
        self.sigma_min = config.get('sigma_min', 60 * 60)
        
        self.adaptive_iou_weight = config.get('adaptive_iou_weight', True)
        self.iou_weight_min = config.get('iou_weight_min', 20)
        self.iou_weight_max = config.get('iou_weight_max', 55)
        self.size_change_threshold = config.get('size_change_threshold', 0.4)
        
        self.stable_track_library: List[StableTrack] = []
        
        self.rematch_count = 0
        
        self._stable_frame_counter: Dict[int, int] = {}
        
        self._current_iou_weight = self.iou_weight
    
    def _distance_sq(self, x1: int, y1: int, x2: int, y2: int) -> int:
        """计算距离平方(无开方)"""
        dx = x1 - x2
        dy = y1 - y2
        return dx * dx + dy * dy
    
    def _calculate_iou(self, box1: Tuple[int, int, int, int], 
                       box2: Tuple[int, int, int, int]) -> int:
        """
        计算IoU（返回整数，范围0-100）
        box格式: (x1, y1, x2, y2)
        使用整数运算避免浮点
        """
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        inter_x1 = max(x1_1, x1_2)
        inter_y1 = max(y1_1, y1_2)
        inter_x2 = min(x2_1, x2_2)
        inter_y2 = min(y2_1, y2_2)
        
        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0
        
        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        if area1 == 0 or area2 == 0:
            return 0
        
        union_area = area1 + area2 - inter_area
        
        if union_area == 0:
            return 100
        
        return (inter_area * 100) // union_area
    
    def _get_prior(self, lost_frames: int) -> Tuple[int, int]:
        """获取先验概率 P(H0) 和 P(H1)"""
        if lost_frames == 1:
            p_h0 = self.prior_lost_1
        elif lost_frames <= 3:
            p_h0 = self.prior_lost_2_3
        elif lost_frames <= 8:
            p_h0 = self.prior_lost_4_8
        else:
            p_h0 = self.prior_lost_9_plus
        return p_h0, 100 - p_h0
    
    def _get_dist_likelihood(self, d_sq: int) -> Tuple[int, int]:
        """获取距离似然度 P(D_dist|H0) 和 P(D_dist|H1)"""
        sigma_sixth = self.sigma_sq // 6
        sigma_third = self.sigma_sq // 3
        
        if d_sq < sigma_sixth:
            p_d_h0 = self.dist_likelihood_very_near
        elif d_sq < sigma_third:
            p_d_h0 = self.dist_likelihood_near
        elif d_sq < self.sigma_sq:
            p_d_h0 = self.dist_likelihood_medium
        else:
            p_d_h0 = self.dist_likelihood_far
        
        return p_d_h0, 100 - p_d_h0
    
    def _get_iou_likelihood(self, iou_int: int) -> Tuple[int, int]:
        """获取IoU似然度 P(D_iou|H0) 和 P(D_iou|H1)
        iou_int: IoU值乘以100的整数（范围0-100）
        """
        if iou_int >= 50:
            p_d_h0 = self.iou_likelihood_very_high
        elif iou_int >= 30:
            p_d_h0 = self.iou_likelihood_high
        elif iou_int >= 15:
            p_d_h0 = self.iou_likelihood_medium
        elif iou_int >= 5:
            p_d_h0 = self.iou_likelihood_low
        else:
            p_d_h0 = self.iou_likelihood_none
        
        return p_d_h0, 100 - p_d_h0
    
    def _update_stable_library(self, tracked_ids_this_frame: set):
        """更新稳定轨迹库：只增加丢失轨迹的lost_frames"""
        updated = []
        for track in self.stable_track_library:
            if track.track_id in tracked_ids_this_frame:
                track.lost_frames = 0
            else:
                track.lost_frames += 1
            if track.lost_frames <= self.max_lost_frames:
                updated.append(track)
        self.stable_track_library = updated
    
    def _adaptive_adjust_sigma(self, new_detections: List[Tuple[int, int, int, int]]):
        """自适应调整抖动方差"""
        if not self.adaptive_sigma:
            return
        
        near_old_count = 0
        for x_new, y_new, _, _ in new_detections:
            for track in self.stable_track_library:
                d_sq = self._distance_sq(x_new, y_new, track.center_x, track.center_y)
                if d_sq < self.sigma_sq:
                    near_old_count += 1
                    break
        
        if near_old_count >= self.sigma_increase_threshold:
            self.sigma_sq = min(self.sigma_sq + 500, self.sigma_max)
        else:
            self.sigma_sq = max(self.sigma_sq - 100, self.sigma_min)
    
    def _adaptive_adjust_iou_weight(self, tracked_objects: List[Dict[str, Any]]):
        """自适应调整IoU权重：检测到尺寸剧烈变化时降低IoU权重"""
        if not self.adaptive_iou_weight or not tracked_objects:
            return
        
        size_change_count = 0
        total_checked = 0
        
        for tracked in tracked_objects:
            track_id = tracked['track_id']
            box = tracked['box']
            curr_w = box[2] - box[0]
            curr_h = box[3] - box[1]
            
            for track in self.stable_track_library:
                if track.track_id == track_id and track.box_w > 0 and track.box_h > 0:
                    w_ratio = abs(curr_w - track.box_w) / max(track.box_w, 1)
                    h_ratio = abs(curr_h - track.box_h) / max(track.box_h, 1)
                    avg_change = (w_ratio + h_ratio) / 2
                    
                    if avg_change > self.size_change_threshold:
                        size_change_count += 1
                    total_checked += 1
                    break
        
        if total_checked == 0:
            return
        
        change_ratio = size_change_count / total_checked
        
        if change_ratio > 0.5:
            self._current_iou_weight = max(
                self._current_iou_weight - 5, 
                self.iou_weight_min
            )
        elif change_ratio < 0.2:
            self._current_iou_weight = min(
                self._current_iou_weight + 2, 
                self.iou_weight_max
            )
    
    def update_stable_tracks(self, tracked_objects: List[Dict[str, Any]]):
        """更新稳定轨迹库（每帧调用）"""
        tracked_ids_this_frame = set()
        for tracked in tracked_objects:
            track_id = tracked['track_id']
            tracked_ids_this_frame.add(track_id)
            
            box = tracked['box']
            cx = (box[0] + box[2]) // 2
            cy = (box[1] + box[3]) // 2
            bw = box[2] - box[0]
            bh = box[3] - box[1]
            
            if track_id not in self._stable_frame_counter:
                self._stable_frame_counter[track_id] = 0
            self._stable_frame_counter[track_id] += 1
            
            if self._stable_frame_counter[track_id] >= self.min_stable_frames:
                existing = None
                for i, t in enumerate(self.stable_track_library):
                    if t.track_id == track_id:
                        existing = i
                        break
                
                if existing is not None:
                    self.stable_track_library[existing].center_x = cx
                    self.stable_track_library[existing].center_y = cy
                    self.stable_track_library[existing].box_w = bw
                    self.stable_track_library[existing].box_h = bh
                    self.stable_track_library[existing].lost_frames = 0
                    self.stable_track_library[existing].hit_count += 1
                else:
                    self.stable_track_library.append(StableTrack(
                        track_id=track_id,
                        center_x=cx,
                        center_y=cy,
                        box_w=bw,
                        box_h=bh,
                        lost_frames=0,
                        class_id=tracked.get('class_id', 0),
                        label=tracked.get('label', ''),
                        hit_count=1
                    ))
        
        self._update_stable_library(tracked_ids_this_frame)
        self._adaptive_adjust_iou_weight(tracked_objects)
    
    def try_rematch(self, detection: Dict[str, Any], 
                   tracked_ids_this_frame: set,
                   valid_track_ids: set = None) -> Optional[int]:
        """
        尝试为检测框恢复ID（支持距离+IoU双证据融合）
        
        :param detection: 检测框信息 {'box': [x1,y1,x2,y2], ...}
        :param tracked_ids_this_frame: 当前帧已跟踪的ID集合
        :param valid_track_ids: 有效的tracker ID集合（只匹配这些ID）
        :return: 恢复的ID，如果无法恢复返回None
        """
        box = detection['box']
        cx = (box[0] + box[2]) // 2
        cy = (box[1] + box[3]) // 2
        det_box = (box[0], box[1], box[2], box[3])
        
        best_match_id = None
        best_score_old = 0
        best_score_new = 0
        
        w_dist = 100 - self._current_iou_weight
        w_iou = self._current_iou_weight
        
        for track in self.stable_track_library:
            if track.lost_frames == 0:
                continue
            if track.track_id in tracked_ids_this_frame:
                continue
            if valid_track_ids is not None and track.track_id not in valid_track_ids:
                continue
            
            p_h0, p_h1 = self._get_prior(track.lost_frames)
            
            d_sq = self._distance_sq(cx, cy, track.center_x, track.center_y)
            p_dist_h0, p_dist_h1 = self._get_dist_likelihood(d_sq)
            
            score_dist_old = p_h0 * p_dist_h0
            score_dist_new = p_h1 * p_dist_h1
            
            if self.enable_iou and w_iou > 0:
                old_box = (
                    track.center_x - track.box_w // 2,
                    track.center_y - track.box_h // 2,
                    track.center_x + track.box_w // 2,
                    track.center_y + track.box_h // 2
                )
                iou_int = self._calculate_iou(det_box, old_box)
                
                if iou_int < self.iou_min_threshold:
                    continue
                
                p_iou_h0, p_iou_h1 = self._get_iou_likelihood(iou_int)
                
                score_iou_old = p_h0 * p_iou_h0
                score_iou_new = p_h1 * p_iou_h1
                
                score_old = (w_dist * score_dist_old + w_iou * score_iou_old) // 100
                score_new = (w_dist * score_dist_new + w_iou * score_iou_new) // 100
            else:
                score_old = score_dist_old
                score_new = score_dist_new
            
            if score_old > best_score_old and score_old > score_new:
                best_score_old = score_old
                best_score_new = score_new
                best_match_id = track.track_id
        
        if best_match_id is not None:
            self.rematch_count += 1
            
            for i, t in enumerate(self.stable_track_library):
                if t.track_id == best_match_id:
                    self.stable_track_library[i].center_x = cx
                    self.stable_track_library[i].center_y = cy
                    self.stable_track_library[i].box_w = box[2] - box[0]
                    self.stable_track_library[i].box_h = box[3] - box[1]
                    self.stable_track_library[i].lost_frames = 0
                    self.stable_track_library[i].hit_count += 1
                    break
        
        return best_match_id
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'rematch_count': self.rematch_count,
            'stable_library_size': len(self.stable_track_library),
            'sigma_sq': self.sigma_sq,
            'iou_enabled': self.enable_iou,
            'current_iou_weight': self._current_iou_weight,
            'iou_weight_config': self.iou_weight,
        }
    
    def reset(self):
        """重置匹配器状态"""
        self.stable_track_library.clear()
        self._stable_frame_counter.clear()
        self.rematch_count = 0
        self._current_iou_weight = self.iou_weight
