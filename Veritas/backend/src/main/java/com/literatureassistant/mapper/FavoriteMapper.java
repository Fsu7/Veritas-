package com.literatureassistant.mapper;

import com.literatureassistant.dto.response.FavoriteResponse;
import com.literatureassistant.entity.Paper;
import com.literatureassistant.entity.PaperFavorite;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

/**
 * 论文收藏 Mapper（MapStruct）。
 * <p>将 PaperFavorite + Paper 合并转换为 FavoriteResponse。
 * <p>task36 新建。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.5
 */
@Mapper(componentModel = "spring", uses = {JsonStringListHelper.class})
public interface FavoriteMapper {

    @Mapping(target = "favoriteId", source = "favorite.id")
    @Mapping(target = "paperId", source = "paper.paperId")
    @Mapping(target = "title", source = "paper.title")
    @Mapping(target = "authors", source = "paper.authors", qualifiedByName = "jsonToList")
    @Mapping(target = "year", source = "paper.year")
    @Mapping(target = "venue", source = "paper.venue")
    @Mapping(target = "citationCount", source = "paper.citationCount")
    @Mapping(target = "createdAt", source = "favorite.createdAt")
    FavoriteResponse toResponse(PaperFavorite favorite, Paper paper);
}
