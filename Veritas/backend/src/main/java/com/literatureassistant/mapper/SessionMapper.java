package com.literatureassistant.mapper;

import com.literatureassistant.dto.response.SessionDetailResponse;
import com.literatureassistant.dto.response.SessionResponse;
import com.literatureassistant.entity.Session;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(componentModel = "spring")
public interface SessionMapper {

    @Mapping(target = "status", expression = "java(session.getStatus().getDbValue())")
    SessionResponse toResponse(Session session);

    @Mapping(target = "status", expression = "java(session.getStatus().getDbValue())")
    @Mapping(target = "analysisCount", ignore = true)
    SessionDetailResponse toDetailResponse(Session session);
}
