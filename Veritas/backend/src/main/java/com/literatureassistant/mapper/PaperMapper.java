package com.literatureassistant.mapper;

import com.literatureassistant.dto.response.PaperDetailResponse;
import com.literatureassistant.dto.response.PaperResponse;
import com.literatureassistant.entity.Paper;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(componentModel = "spring", uses = {JsonStringListHelper.class})
public interface PaperMapper {

    @Mapping(target = "authors", source = "authors", qualifiedByName = "jsonToList")
    @Mapping(target = "keywords", source = "keywords", qualifiedByName = "jsonToList")
    PaperResponse toResponse(Paper paper);

    @Mapping(target = "authors", source = "authors", qualifiedByName = "jsonToList")
    @Mapping(target = "keywords", source = "keywords", qualifiedByName = "jsonToList")
    PaperDetailResponse toDetailResponse(Paper paper);
}
